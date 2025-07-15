from typing import List, Dict, Any
from github import Github
from os import getenv
from agno.tools import tool


@tool
def fetch_pr_comments(repo_name: str, pr_number: int, only_recent: bool = True) -> str:
    """Fetch comments from a pull request, optionally filtering to only recent ones.
    
    Args:
        repo_name (str): The full name of the repository (e.g., 'owner/repo')
        pr_number (int): The number of the pull request
        only_recent (bool): If True, only fetch comments after the last commit
        
    Returns:
        str: Formatted string containing PR comments with file paths and line numbers
    """
    try:
        access_token = getenv("GITHUB_ACCESS_TOKEN")
        if not access_token:
            return "Error: GITHUB_ACCESS_TOKEN not found"
            
        g = Github(access_token)
        repo = g.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        
        last_commit_time = None
        if only_recent:
            commits = list(pr.get_commits())
            if commits:
                last_commit_time = commits[-1].commit.committer.date
        
        comments_data = []
        
        review_comments = pr.get_review_comments()
        for comment in review_comments:
            if only_recent and last_commit_time and comment.created_at < last_commit_time:
                continue
                
            comments_data.append({
                "type": "review",
                "file": comment.path,
                "line": comment.line or comment.original_line,
                "body": comment.body,
                "author": comment.user.login,
                "created_at": comment.created_at.isoformat()
            })
            
        if not comments_data:
            return "No comments found on this PR"
            
        filter_msg = " (after last commit)" if only_recent and last_commit_time else ""
        formatted_comments = f"Found {len(comments_data)} comments{filter_msg} on PR #{pr_number}:\n\n"
        
        for i, comment in enumerate(comments_data, 1):
            formatted_comments += f"## Comment {i}\n"
            formatted_comments += f"**Type**: {comment['type']}\n"
            formatted_comments += f"**Author**: {comment['author']}\n"
            if comment['file']:
                formatted_comments += f"**File**: {comment['file']}\n"
                formatted_comments += f"**Line**: {comment['line']}\n"
            formatted_comments += f"**Content**:\n{comment['body']}\n\n"
            formatted_comments += "---\n\n"
            
        return formatted_comments
        
    except Exception as e:
        return f"Error fetching PR comments: {str(e)}"