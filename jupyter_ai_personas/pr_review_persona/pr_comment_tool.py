from github import Github, GithubException
from os import getenv

def create_pr_comment_with_head_sha(repo_name: str, pr_number: int, body: str, path: str, position: int) -> str:
    """Create a comment on a specific line of a specific file in a pull request using the head commit SHA.
    
    Args:
        repo_name (str): The full name of the repository (e.g., 'owner/repo').
        pr_number (int): The number of the pull request.
        body (str): The text of the comment.
        path (str): The relative path to the file to comment on.
        position (int): The line index in the diff to comment on.
    
    Returns:
        str: Success message or error.
    """
    try:
        access_token = getenv("GITHUB_ACCESS_TOKEN")
        if not access_token:
            return "Error: GITHUB_ACCESS_TOKEN not found"
        
        g = Github(access_token)
        repo = g.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        head_repo = pr.head.repo
        commit = head_repo.get_commit(pr.head.sha)
        comment = pr.create_comment(body, commit, path, position)
        
        return f"Comment created successfully: {comment.html_url}"
    except GithubException as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"
    
