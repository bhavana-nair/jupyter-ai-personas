from typing import List, Dict, Any, Union
from github import Github
from os import getenv
from agno.tools import tool
import base64
import json


@tool
def apply_code_fixes(repo_name: str, pr_number: int, fixes: Union[List[Dict[str, Any]], str]) -> str:
    """Apply code fixes to files in a pull request.
    
    Args:
        repo_name (str): The full name of the repository (e.g., 'owner/repo')
        pr_number (int): The number of the pull request
        fixes (List[Dict]): List of fix objects with structure:
            [
                {
                    "file_path": "path/to/file.py",
                    "old_content": "content to replace",
                    "new_content": "replacement content",
                    "reason": "explanation of the fix"
                }
            ]
            
    Returns:
        str: Success message or error details
    """
    try:
        # Handle string input (JSON) by parsing it
        if isinstance(fixes, str):
            try:
                fixes = json.loads(fixes)
            except json.JSONDecodeError:
                return "Error: Invalid JSON format for fixes"
        
        access_token = getenv("GITHUB_ACCESS_TOKEN")
        if not access_token:
            return "Error: GITHUB_ACCESS_TOKEN not found"
            
        g = Github(access_token)
        repo = g.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        
        # Get the head branch
        head_branch = pr.head.ref
        head_repo = pr.head.repo
        
        applied_fixes = []
        
        for fix in fixes:
            file_path = fix["file_path"]
            old_content = fix["old_content"]
            new_content = fix["new_content"]
            reason = fix.get("reason", "Code fix")
            
            try:
                # Get current file content
                file_obj = head_repo.get_contents(file_path, ref=head_branch)
                current_content = base64.b64decode(file_obj.content).decode('utf-8')
                
                # Apply the fix
                if old_content in current_content:
                    updated_content = current_content.replace(old_content, new_content)
                    
                    # Update the file
                    head_repo.update_file(
                        path=file_path,
                        message=f"Fix: {reason}",
                        content=updated_content,
                        sha=file_obj.sha,
                        branch=head_branch
                    )
                    
                    applied_fixes.append(f"✅ {file_path}: {reason}")
                else:
                    applied_fixes.append(f"⚠️ {file_path}: Content not found for replacement")
                    
            except Exception as file_error:
                applied_fixes.append(f"❌ {file_path}: {str(file_error)}")
                
        return f"Applied {len(applied_fixes)} fixes:\n" + "\n".join(applied_fixes)
        
    except Exception as e:
        return f"Error applying fixes: {str(e)}"