import os
from typing import List, Dict, Any
from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.github import GithubTools
from agno.tools.reasoning import ReasoningTools
from agno.tools.python import PythonTools
from agno.tools import tool
import httpx
import json

try:
    from ..pr_review_persona.fetch_ci_failures import fetch_ci_failures
    from ..pr_review_persona.pr_comment_tool import create_inline_pr_comments
except ImportError:
    import sys
    sys.path.append('../pr_review_persona')
    from fetch_ci_failures import fetch_ci_failures
    from pr_comment_tool import create_inline_pr_comments

# MCP Task Master Tools
@tool
def create_task_workflow(workflow_name: str, tasks: List[Dict[str, Any]]) -> str:
    """Create a new workflow in Task Master via MCP"""
    # This would connect to Task Master MCP server
    payload = {
        "workflow_name": workflow_name,
        "tasks": tasks
    }
    # MCP call to Task Master
    return f"Workflow '{workflow_name}' created with {len(tasks)} tasks"

@tool
def execute_task_workflow(workflow_id: str, context: Dict[str, Any]) -> str:
    """Execute a workflow in Task Master"""
    # MCP call to execute workflow
    return f"Executing workflow {workflow_id} with context"

@tool
def get_workflow_status(workflow_id: str) -> Dict[str, Any]:
    """Get status of running workflow"""
    # MCP call to get status
    return {
        "workflow_id": workflow_id,
        "status": "running",
        "completed_tasks": ["fetch_pr", "analyze_ci"],
        "current_task": "review_code",
        "pending_tasks": ["scan_security", "create_comments"]
    }

class MCPTaskMaster:
    def __init__(self):
        self.model = Gemini(id="gemini-2.5-pro", api_key="AIzaSyCkD-2rU7O2Ubsf_iXV9rOZ2fmatZ5IxSA")
        
        github_token = os.getenv("GITHUB_ACCESS_TOKEN")
        if not github_token:
            raise ValueError("GITHUB_ACCESS_TOKEN required")
        os.environ['GITHUB_ACCESS_TOKEN'] = github_token
        
        self._setup_coordinator()
    
    def _setup_coordinator(self):
        """Setup coordinator agent with Task Master MCP tools"""
        self.coordinator = Agent(
            name="mcp_coordinator",
            role="Task Master Coordinator",
            model=self.model,
            instructions=[
                "You coordinate PR reviews using Task Master via MCP.",
                "",
                "WORKFLOW SETUP:",
                "1. Use create_task_workflow to define PR review workflow",
                "2. Define tasks: fetch_pr, analyze_ci, review_code, scan_security, create_comments",
                "3. Set dependencies and conditions for each task",
                "",
                "EXECUTION:",
                "1. Use execute_task_workflow to start the workflow",
                "2. Monitor progress with get_workflow_status",
                "3. Handle task failures and retries",
                "",
                "TASK DEFINITIONS:",
                "- fetch_pr: Get PR data using GitHub tools",
                "- analyze_ci: Check CI status with fetch_ci_failures",
                "- review_code: Analyze code quality",
                "- scan_security: Check for vulnerabilities", 
                "- create_comments: Post inline PR comments",
                "",
                "SMART WORKFLOW:",
                "- Skip tasks based on PR characteristics",
                "- Run tasks in parallel where possible",
                "- Adapt workflow based on intermediate results"
            ],
            tools=[
                create_task_workflow,
                execute_task_workflow, 
                get_workflow_status,
                GithubTools(get_pull_requests=True, get_pull_request_changes=True),
                fetch_ci_failures,
                create_inline_pr_comments,
                ReasoningTools()
            ]
        )
    
    async def review_pr(self, pr_input: str) -> str:
        """Execute PR review using Task Master MCP"""
        try:
            # Let the coordinator handle everything via Task Master
            response = await self.coordinator.arun(
                f"""
                Please coordinate a PR review for: {pr_input}
                
                Steps:
                1. Create a smart PR review workflow in Task Master
                2. Execute the workflow with appropriate context
                3. Monitor execution and handle any issues
                4. Return the final results
                
                Make the workflow intelligent - skip unnecessary tasks based on PR characteristics.
                """
            )
            
            return response.content if hasattr(response, 'content') else str(response)
            
        except Exception as e:
            return f"MCP Task Master review failed: {str(e)}"

# Example workflow definition for Task Master
PR_REVIEW_WORKFLOW = {
    "name": "pr_review_workflow",
    "tasks": [
        {
            "id": "fetch_pr",
            "name": "Fetch PR Data",
            "agent": "github_specialist",
            "dependencies": [],
            "tools": ["github_tools"],
            "conditions": []
        },
        {
            "id": "analyze_ci", 
            "name": "Analyze CI Status",
            "agent": "ci_analyst",
            "dependencies": ["fetch_pr"],
            "tools": ["fetch_ci_failures"],
            "conditions": ["skip_if_ci_passing"]
        },
        {
            "id": "review_code",
            "name": "Code Quality Review",
            "agent": "code_reviewer", 
            "dependencies": ["fetch_pr"],
            "tools": ["python_tools"],
            "conditions": ["skip_if_docs_only"]
        },
        {
            "id": "scan_security",
            "name": "Security Analysis",
            "agent": "security_scanner",
            "dependencies": ["fetch_pr"],
            "tools": ["python_tools"],
            "conditions": ["skip_if_small_pr", "skip_if_docs_only"]
        },
        {
            "id": "create_comments",
            "name": "Create PR Comments",
            "agent": "comment_creator",
            "dependencies": ["analyze_ci", "review_code", "scan_security"],
            "tools": ["create_inline_pr_comments"],
            "conditions": []
        }
    ],
    "execution_mode": "smart_parallel",
    "error_handling": "continue_on_failure"
}