from typing import Any, Dict, List
from github import Github, GithubException
from os import getenv
from agno.tools import tool

@tool
def create_inline_pr_comments(repo_name: str, pr_number: int, comments: List[Dict[str, Any]]) -> str:
    """Create multiple inline comments on a pull request.
    
    Args:
        repo_name (str): The full name of the repository (e.g., 'owner/repo').
        pr_number (int): The number of the pull request.
        comments (List[Dict]): List of comment objects with the following structure:
            [
                {
                    "path": "path/to/file.py",  # Relative file path
                    "position": 10,            # Line number in the file
                    "body": "Comment text"      # The comment text
                },
                ...
            ]
    
    Returns:
        str: Success message with URLs of created comments or error.
    """
    print(f"[DEBUG] create_inline_pr_comments called with repo={repo_name}, pr={pr_number}, comments={len(comments) if comments else 0}")
    if comments:
        print(f"[DEBUG] First comment: {comments[0]}")
    else:
        print(f"[DEBUG] No comments provided - agent called tool with empty list")
    try:
        access_token = getenv("GITHUB_ACCESS_TOKEN")
        if not access_token:
            return "Error: GITHUB_ACCESS_TOKEN not found"
        
        g = Github(access_token)
        repo = g.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        head_repo = pr.head.repo
        commit = head_repo.get_commit(pr.head.sha)
        
        print(f"[DEBUG] About to create {len(comments)} inline comments")
        
        # Skip summary comment for now - focus on inline comments only
        # summary = "## 👋 PR Review Complete!\n\n"
        # summary += "I've reviewed your changes and left some feedback inline. "
        # summary += f"Found {len(comments)} items to discuss. "
        # summary += "Check out the individual comments for details! ✨"
        # pr.create_issue_comment(summary)
        
        # Create all inline comments
        comment_urls = []
        for i, comment_data in enumerate(comments):
            try:
                print(f"[DEBUG] Creating comment {i+1}: path={comment_data.get('path')}, position={comment_data.get('position')}, body={comment_data.get('body')[:50]}...")
                
                # Use create_review_comment with correct parameters
                comment = pr.create_review_comment(
                    body=comment_data["body"],
                    commit=commit,
                    path=comment_data["path"],
                    line=comment_data["position"]
                )
                comment_urls.append(comment.html_url)
                print(f"[DEBUG] Comment {i+1} created successfully: {comment.html_url}")
            except Exception as comment_error:
                print(f"[DEBUG] Failed to create comment {i+1}: {str(comment_error)}")
                continue
        
        return f"Posted review summary and {len(comment_urls)} inline comments"
    except GithubException as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"
    

    
