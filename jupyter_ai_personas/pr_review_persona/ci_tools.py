import os
import json
from time import sleep
from typing import List, Dict, Optional
from agno.tools import Toolkit
from agno.utils.log import logger
import re
from github import Github
import requests
from ratelimit import limits, sleep_and_retry
from agno.agent import Agent

GITHUB_RATE_LIMIT = 5000  # GitHub API rate limit per hour
CALLS_PER_HOUR = GITHUB_RATE_LIMIT

@sleep_and_retry
@limits(calls=CALLS_PER_HOUR, period=3600)
def rate_limited_request(url: str, headers: Dict[str, str]) -> requests.Response:
    """Make a rate-limited request to the GitHub API"""
    response = requests.get(url, headers=headers)
    if response.status_code == 403 and 'rate limit exceeded' in response.text.lower():
        logger.warning("GitHub API rate limit exceeded. Waiting...")
        sleep(3600)  # Wait for rate limit reset
        response = requests.get(url, headers=headers)
    return response

class CITools(Toolkit):
    def __init__(self, **kwargs):
        # Securely retrieve and validate GitHub token
        self.github_token = self._validate_github_token()
        
        super().__init__(name="ci_tools", tools=[
            self.fetch_ci_failure_data,
            self.get_ci_logs
        ],  **kwargs)

    def _validate_github_token(self) -> Optional[str]:
        """Validate GitHub access token from environment variables"""
        token = os.getenv("GITHUB_ACCESS_TOKEN")
        if not token:
            logger.warning("GITHUB_ACCESS_TOKEN environment variable is not set. GitHub operations will be limited.")
            return None
        
        # Basic token format validation
        if not re.match(r'^(gh[ps]_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59})$', token):
            logger.warning("Invalid GitHub token format. Please check your token.")
            return None
            
        return token

    async def fetch_ci_failure_data(self, agent: Agent, repo_url: str, pr_number: int) -> List[Dict[str, str]]:
        """
        Fetch CI Failure data from GitHub API and store it in the agent's session state.
        
        Args:
            agent (Agent): The agent instance to store logs in session state
            repo_url (str): URL of the GitHub repository, must be in format 'github.com/owner/repo'
            pr_number (int): Pull request number, must be positive
            
        Returns:
            List[Dict[str, str]]: List of failure data containing job name, id and log information
            
        Raises:
            ValueError: If repo_url format is invalid or pr_number is not positive
            RuntimeError: If GitHub API calls fail or rate limit is exceeded
        """
        # Validate inputs
        if not isinstance(pr_number, int) or pr_number <= 0:
            raise ValueError("pr_number must be a positive integer")
            
        if not self.github_token:
            raise RuntimeError("GitHub token is not set or invalid")
        match = None
        if "github.com" in repo_url:
            match = re.search(r"github\.com/([^/]+)/([^/]+)", repo_url)
            
        if not match:
            raise ValueError("Invalid GitHub URL format. Expected either github.com/owner/repo or api.github.com/repos/owner/repo")

        owner, repo_name = match.groups()
        repo_name = f"{owner}/{repo_name}"

        g = Github(os.getenv("GITHUB_ACCESS_TOKEN"))
        repo = g.get_repo(repo_name)
        pr_data = repo.get_pull(pr_number)

        runs = repo.get_workflow_runs(branch=pr_data.head.ref)
        failures = []

        for run in runs:
            if run.head_sha == pr_data.head.sha:
                logger.debug(f"Processing workflow run {run.id} for repo {repo_name}")
                jobs = run.jobs()

                for job in jobs:
                    if job.conclusion == "failure":
                        logger.info(f"Found failed job: {job.name} (ID: {job.raw_data['id']})")
                        
                        job_id = job.raw_data["id"]
                        
                        headers = {
                            "Accept": "application/vnd.github+json",
                            "Authorization": f"Bearer {self.github_token}",
                            "X-GitHub-Api-Version": "2022-11-28",
                            "User-Agent": "PRReviewPersona/1.0"
                        }
                        log_url = f"https://api.github.com/repos/{repo_name}/actions/jobs/{job_id}/logs"
                        log_response = requests.get(log_url, headers=headers)
                        
                        if log_response.status_code != 200:
                            raise Exception(f"Failed to fetch logs: {log_response.status_code} {log_response.text} from {log_url}")
                        log_content = log_response.text

                        ##If seeing ThrottlingException in test aws account uncomment these lines [81-87] and line  92 AND comment line 93

                        # # Extract key error lines from the log
                        # log_lines = log_content.splitlines()
                        # error_lines = []
                        # for line in log_lines[-20:]:  
                        #     if 'error:' in line.lower() or 'fail:' in line.lower():
                        #         error_lines.append(line)
                        #         if len(error_lines) >= 10: 
                        #             break
                        
                        failure_data = {
                            "name": job.name,
                            "id": job_id,
                            # "error_lines": error_lines if error_lines else [log_lines[-1]],  
                            "log": log_content
                        }
                        failures.append(failure_data)

                        if agent.session_state is None:
                            agent.session_state = {}
                        if "ci_logs" not in agent.session_state:
                            agent.session_state["ci_logs"] = []
                        
                        agent.session_state["ci_logs"].append(failure_data)

        print(f"Found {len(failures)} failed jobs")
        return failures

    async def get_ci_logs(self, agent: Agent, job_name: str = None) -> list:
        """
        Retrieve CI failure logs from agent's session state.
        
        Args:
            agent (Agent): The agent instance to access session state
            job_name (str, optional): Filter logs by job name
            
        Returns:
            list: List of failure logs matching the criteria
        """
        # Handle None session_state
        if agent.session_state is None or "ci_logs" not in agent.session_state:
            return []
            
        logs = agent.session_state["ci_logs"]
        if job_name:
            logs = [log for log in logs if log["name"] == job_name]
            
        return logs