import os
import re
import tempfile
import zipfile
import requests
from agno.tools import tool
from github import Github


def _extract_failure_content(log_content: str) -> tuple[str, dict]:
    """Extract only failure-relevant content from CI logs."""
    lines = log_content.split('\n')
    relevant_lines = []
    
    error_patterns = [
        r'(?i)(\berror\b|\bfail\b|exception|traceback|fatal|panic|abort)',
        r'(?i)(test.*fail|assertion.*fail)',
        r'(?i)(build.*fail|compilation.*fail)',
        r'(?i)(timeout|killed|terminated)',
    ]
    
    # Exclude warning
    warning_patterns = [
        r'(?i)warning',
        r'(?i)warn:',
        r'(?i)deprecated',
    ]
    
    for i, line in enumerate(lines):
        if any(re.search(pattern, line) for pattern in error_patterns):
            # Skip if it's just a warning
            if any(re.search(pattern, line) for pattern in warning_patterns):
                continue
            relevant_lines.append(line)
    
    filtered_content = '\n'.join(relevant_lines) if relevant_lines else log_content[:1000]
    
    metrics = {
        'original_lines': len(lines),
        'filtered_lines': len(filtered_content.split('\n')),
        'original_chars': len(log_content),
        'filtered_chars': len(filtered_content),
        'compression_ratio': round(len(filtered_content) / len(log_content) * 100, 2) if log_content else 0
    }
    
    return filtered_content, metrics


@tool
def fetch_ci_failures(repo_name: str, pr_number: int) -> list:
    """
    Fetch CI failure data from GitHub API with optimized log processing.

    Args:
        repo_name (str): Repository in owner/repo format (e.g., 'owner/repo')
        pr_number (int): Pull request number

    Returns:
        list: List of failure data containing job name, id and filtered log information
    """
    github_token = os.getenv("GITHUB_ACCESS_TOKEN")
    if not github_token:
        raise ValueError("GITHUB_ACCESS_TOKEN environment variable is not set")

    repo = Github(github_token).get_repo(repo_name)
    pr_data = repo.get_pull(pr_number)
    runs = repo.get_workflow_runs(branch=pr_data.head.ref)
    failures = []

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {github_token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    for run in runs:
        if run.head_sha == pr_data.head.sha:
            jobs = run.jobs()

            for job in jobs:
                if job.conclusion == "failure":
                    job_id = job.raw_data["id"]
                    
                    log_url = f"https://api.github.com/repos/{repo_name}/actions/jobs/{job_id}/logs"
                    log_response = requests.get(log_url, headers=headers)

                    if log_response.status_code != 200:
                        continue

                    if log_response.headers.get('content-encoding') == 'gzip' or \
                       log_response.headers.get('content-type') == 'application/zip':
                        try:
                            with tempfile.NamedTemporaryFile() as temp_file:
                                temp_file.write(log_response.content)
                                temp_file.flush()
                                
                                with zipfile.ZipFile(temp_file.name, 'r') as zip_file:
                                    log_content = zip_file.read(zip_file.namelist()[0]).decode('utf-8')
                        except:
                            log_content = log_response.text
                    else:
                        log_content = log_response.text

                    filtered_log, metrics = _extract_failure_content(log_content)

                    failure_data = {
                        "name": job.name,
                        "id": job_id,
                        "log": filtered_log,
                        "metrics": metrics,
                    }
                    failures.append(failure_data)

    return failures