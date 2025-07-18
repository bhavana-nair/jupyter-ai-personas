"""Tests for PRCreationPersona."""

import pytest
from unittest.mock import MagicMock, patch
from github import Github
from github.PullRequest import PullRequest
from github.Repository import Repository

from jupyter_ai_personas.pr_creation_persona.persona import PRCreationPersona
from jupyter_ai_personas.exceptions import ConfigurationError, GitHubError

@pytest.fixture
def mock_github():
    """Create mock GitHub client."""
    mock = MagicMock(spec=Github)
    return mock

@pytest.fixture
def mock_repo():
    """Create mock repository."""
    mock = MagicMock(spec=Repository)
    return mock

@pytest.fixture
def mock_pr():
    """Create mock pull request."""
    mock = MagicMock(spec=PullRequest)
    mock.html_url = "https://github.com/org/repo/pull/1"
    mock.number = 1
    mock.id = 12345
    mock.state = "open"
    mock.title = "Test PR"
    mock.body = "PR description"
    mock.draft = False
    return mock

@pytest.fixture
def persona(mock_github):
    """Create PRCreationPersona instance with mocked dependencies."""
    with patch("github.Github", return_value=mock_github):
        config = {
            "github": {
                "token": "test-token"
            }
        }
        return PRCreationPersona(config=config)

async def test_create_pull_request(persona, mock_github, mock_repo, mock_pr):
    """Test successful PR creation."""
    mock_repo.create_pull.return_value = mock_pr
    mock_github.get_repo.return_value = mock_repo
    
    result = await persona.create_pull_request(
        repo_url="org/repo",
        title="Test PR",
        body="PR description",
        head_branch="feature-branch"
    )
    
    assert result["url"] == mock_pr.html_url
    assert result["number"] == mock_pr.number
    assert result["state"] == mock_pr.state
    
    mock_repo.create_pull.assert_called_once_with(
        title="Test PR",
        body="PR description",
        base="main",
        head="feature-branch",
        draft=False
    )

async def test_create_pull_request_missing_branch(persona):
    """Test PR creation fails without head branch."""
    with pytest.raises(ConfigurationError):
        await persona.create_pull_request(
            repo_url="org/repo",
            title="Test PR",
            body="PR description"
        )

async def test_create_pull_request_github_error(persona, mock_github, mock_repo):
    """Test PR creation handles GitHub errors."""
    mock_repo.create_pull.side_effect = Exception("API error")
    mock_github.get_repo.return_value = mock_repo
    
    with pytest.raises(GitHubError):
        await persona.create_pull_request(
            repo_url="org/repo",
            title="Test PR",
            body="PR description",
            head_branch="feature"
        )

async def test_update_pull_request(persona, mock_github, mock_repo, mock_pr):
    """Test successful PR update."""
    mock_repo.get_pull.return_value = mock_pr
    mock_github.get_repo.return_value = mock_repo
    
    updates = {
        "title": "Updated title",
        "body": "Updated description"
    }
    
    result = await persona.update_pull_request(
        repo_url="org/repo",
        pr_number=1,
        updates=updates
    )
    
    assert result["url"] == mock_pr.html_url
    assert result["number"] == mock_pr.number
    mock_pr.edit.assert_called()

async def test_get_pull_request(persona, mock_github, mock_repo, mock_pr):
    """Test successful PR retrieval."""
    mock_repo.get_pull.return_value = mock_pr
    mock_github.get_repo.return_value = mock_repo
    
    result = await persona.get_pull_request(
        repo_url="org/repo",
        pr_number=1
    )
    
    assert result["url"] == mock_pr.html_url
    assert result["number"] == mock_pr.number
    assert result["title"] == mock_pr.title
    assert result["body"] == mock_pr.body
    assert result["state"] == mock_pr.state
    assert result["draft"] == mock_pr.draft

def test_initialization_missing_token():
    """Test persona initialization fails without GitHub token."""
    with pytest.raises(ConfigurationError):
        PRCreationPersona(config={})