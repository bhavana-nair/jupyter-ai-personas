"""PRCreationPersona for automating pull request creation.

This module implements a persona that can create pull requests based on code changes,
including generating PR descriptions and handling GitHub interactions.
"""

from typing import Dict, List, Optional, Any
import asyncio
from github import Github
from github.PullRequest import PullRequest
from github.Repository import Repository

from jupyter_ai_personas.base import BasePersona
from jupyter_ai_personas.exceptions import ConfigurationError, GitHubError

class PRCreationPersona(BasePersona):
    """A persona that helps create and manage pull requests.
    
    This persona assists with:
    - Creating pull requests with descriptive titles and bodies
    - Managing branch creation and code changes
    - Handling GitHub interactions and error cases
    """

    def __init__(self, *args, **kwargs):
        """Initialize the PR Creation persona.
        
        Args:
            *args: Variable length argument list passed to parent
            **kwargs: Arbitrary keyword arguments passed to parent
        
        Raises:
            ConfigurationError: If required GitHub configuration is missing
        """
        super().__init__(*args, **kwargs)
        self.github_token = self._get_github_token()
        self.github_client = Github(self.github_token)

    def _get_github_token(self) -> str:
        """Get GitHub token from configuration.
        
        Returns:
            str: The GitHub authentication token

        Raises:
            ConfigurationError: If GitHub token is not configured
        """
        try:
            return self.config["github"]["token"]
        except KeyError:
            raise ConfigurationError("GitHub token not found in configuration")

    async def create_pull_request(
        self,
        repo_url: str,
        title: str,
        body: str,
        base_branch: str = "main",
        head_branch: str = None,
        draft: bool = False
    ) -> Dict[str, Any]:
        """Create a new pull request.

        Args:
            repo_url: URL of the GitHub repository
            title: Title for the pull request
            body: Detailed description for the pull request
            base_branch: Base branch to merge into (default: "main")
            head_branch: Source branch containing changes (required)
            draft: Whether to create as draft PR (default: False)

        Returns:
            Dict containing PR details including URL and number

        Raises:
            GitHubError: If PR creation fails
            ConfigurationError: If required parameters are missing
        """
        if not head_branch:
            raise ConfigurationError("Head branch name is required")

        try:
            repo = self.github_client.get_repo(repo_url)
            pr = repo.create_pull(
                title=title,
                body=body,
                base=base_branch,
                head=head_branch,
                draft=draft
            )
            return {
                "url": pr.html_url,
                "number": pr.number,
                "id": pr.id,
                "state": pr.state
            }
        except Exception as e:
            raise GitHubError(f"Failed to create pull request: {str(e)}")

    async def update_pull_request(
        self,
        repo_url: str,
        pr_number: int,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing pull request.

        Args:
            repo_url: URL of the GitHub repository  
            pr_number: Number of the PR to update
            updates: Dictionary of fields to update (title, body, etc)

        Returns:
            Dict containing updated PR details

        Raises:
            GitHubError: If PR update fails
        """
        try:
            repo = self.github_client.get_repo(repo_url)
            pr = repo.get_pull(pr_number)
            
            if "title" in updates:
                pr.edit(title=updates["title"])
            if "body" in updates:
                pr.edit(body=updates["body"])
            if "state" in updates:
                pr.edit(state=updates["state"])

            return {
                "url": pr.html_url,
                "number": pr.number,
                "state": pr.state
            }
        except Exception as e:
            raise GitHubError(f"Failed to update PR #{pr_number}: {str(e)}")
            
    async def get_pull_request(
        self,
        repo_url: str,
        pr_number: int
    ) -> Dict[str, Any]:
        """Get details about a specific pull request.

        Args:
            repo_url: URL of the GitHub repository
            pr_number: Number of the PR to retrieve

        Returns:
            Dict containing PR details

        Raises:
            GitHubError: If PR retrieval fails
        """
        try:
            repo = self.github_client.get_repo(repo_url)
            pr = repo.get_pull(pr_number)
            return {
                "url": pr.html_url,
                "number": pr.number,
                "title": pr.title,
                "body": pr.body,
                "state": pr.state,
                "draft": pr.draft
            }
        except Exception as e:
            raise GitHubError(f"Failed to get PR #{pr_number}: {str(e)}")