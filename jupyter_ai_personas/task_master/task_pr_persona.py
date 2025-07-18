"""Task-based PR Creation Persona for implementing tasks from TaskMaster."""

import os
import re
import boto3
from typing import List, Dict, Any, Optional

from jupyter_ai.personas.base_persona import BasePersona, PersonaDefaults
from jupyterlab_chat.models import Message
from jupyter_ai.history import YChatHistory
from langchain_core.messages import HumanMessage

from agno.agent import Agent
from agno.models.aws import AwsBedrock
from agno.tools.github import GithubTools
from agno.tools.reasoning import ReasoningTools
from agno.tools.file import FileTools
from agno.tools.shell import ShellTools
from agno.tools.python import PythonTools
from agno.team.team import Team

from .prd_agent import PRDAgent
from .taskmaster_client import TaskMasterClient, Task

class TaskPRPersona(BasePersona):
    """Persona that handles task-based PR creation workflow."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.taskmaster = None
        self.prd_agent = None
        self.current_repo_url = None
        self.current_issue_url = None
        self.current_prd = None
        self.current_tasks = []

    @property
    def defaults(self):
        return PersonaDefaults(
            name="TaskPRPersona",
            avatar_path="/api/ai/static/jupyternaut.svg",
            description="A specialized assistant for implementing tasks from GitHub issues using TaskMaster.",
            system_prompt="You are a task-based PR creation assistant that analyzes GitHub issues, creates PRDs, breaks them down into tasks, and implements solutions.",
        )

    def _initialize_agents(self):
        """Initialize the PRD agent and TaskMaster client if not already done."""
        if self.prd_agent is None:
            model_id = self.config_manager.lm_provider_params["model_id"]
            session = boto3.Session()
            self.prd_agent = PRDAgent(model_id=model_id, session=session)
            
        if self.taskmaster is None:
            self.taskmaster = TaskMasterClient()

    def _parse_command(self, message: str) -> Dict[str, Any]:
        """Parse user command to determine action and parameters."""
        # Check for issue URL
        issue_match = re.search(r'(https://github\.com/[^/\s]+/[^/\s]+/issues/\d+)', message)
        if issue_match:
            return {
                "action": "process_issue",
                "issue_url": issue_match.group(1)
            }
            
        # Check for task details command
        task_details_match = re.search(r'(?:show|get|display)\s+task\s+(?:details|info)?\s+(?:for|of)?\s*[#]?(\d+)', message, re.IGNORECASE)
        if task_details_match:
            return {
                "action": "show_task_details",
                "task_id": task_details_match.group(1)
            }
            
        # Check for implementation details command
        impl_details_match = re.search(r'(?:show|get|display)\s+(?:implementation|code)\s+(?:details|info)?\s+(?:for|of)?\s*[#]?(\d+)', message, re.IGNORECASE)
        if impl_details_match:
            return {
                "action": "show_implementation_details",
                "task_id": impl_details_match.group(1)
            }
            
        # Check for implement all tasks command
        if re.search(r'implement\s+all\s+tasks', message, re.IGNORECASE):
            return {
                "action": "implement_all_tasks"
            }
            
        # Check for implement specific task command
        impl_task_match = re.search(r'implement\s+task\s*[#]?(\d+)', message, re.IGNORECASE)
        if impl_task_match:
            return {
                "action": "implement_task",
                "task_id": impl_task_match.group(1)
            }
            
        # Check for list tasks command
        if re.search(r'(?:list|show|get)\s+(?:all\s+)?tasks', message, re.IGNORECASE):
            return {
                "action": "list_tasks"
            }
            
        # Default to help
        return {
            "action": "help"
        }

    def initialize_team(self, system_prompt, task=None):
        """Initialize the PR creation team for implementing a task."""
        model_id = self.config_manager.lm_provider_params["model_id"]
        session = boto3.Session()
        
        github_token = os.getenv("GITHUB_ACCESS_TOKEN")
        if not github_token:
            raise ValueError("GITHUB_ACCESS_TOKEN environment variable is not set. Please set it with a plain GitHub personal access token.")

        # Task Implementer Agent
        task_implementer = Agent(
            name="task_implementer",
            role="Task Implementation Specialist",
            model=AwsBedrock(id=model_id, session=session),
            markdown=True,
            instructions=[
                "MANDATORY TASK IMPLEMENTATION WORKFLOW:",
                
                "STEP 1 - Task Analysis:",
                "   - Understand the task requirements and acceptance criteria",
                "   - Identify the files that need to be modified",
                "   - Plan the implementation approach",
                
                "STEP 2 - Repository Setup:",
                "   - Clone repository using shell commands",
                "   - Create feature branch with descriptive name",
                "   - Verify current codebase state",
                
                "STEP 3 - Code Implementation:",
                "   - Write MINIMAL code that addresses the task requirements",
                "   - Follow existing code patterns and style",
                "   - Implement proper error handling",
                "   - Focus ONLY on the specific task requirements",
                
                "STEP 4 - Testing:",
                "   - Write appropriate tests for the implementation",
                "   - Ensure tests pass",
                
                "CRITICAL REQUIREMENTS:",
                "- Write ONLY the minimal code needed",
                "- Follow existing patterns exactly",
                "- NO verbose implementations",
                "- Focus on the specific task only"
            ],
            tools=[
                ShellTools(),
                FileTools(),
                PythonTools(),
                ReasoningTools(add_instructions=True, think=True, analyze=True)
            ]
        )

        # Git Operations Agent
        git_manager = Agent(
            name="git_manager",
            role="Git Operations Manager",
            model=AwsBedrock(id=model_id, session=session),
            markdown=True,
            instructions=[
                "MANDATORY GIT WORKFLOW:",
                
                "STEP 1 - Repository Operations:",
                "   - Use shell commands for git operations",
                "   - Clone main branch from repository",
                "   - Verify repository state and structure",
                
                "STEP 2 - Branch Management:",
                "   - Create feature branch: git checkout -b feature/task-description",
                "   - Use descriptive branch names based on task",
                "   - Ensure branch is created from latest main",
                
                "STEP 3 - Commit Operations:",
                "   - Stage files: git add .",
                "   - Create clear commit messages: git commit -m 'description'",
                "   - Follow conventional commit format if used in repo",
                
                "STEP 4 - Push Operations:",
                "   - Push feature branch: git push -u origin branch-name",
                "   - DO NOT create pull request (user will do manually)",
                
                "CRITICAL REQUIREMENTS:",
                "- NEVER create pull requests automatically",
                "- Always push to feature branch, never main",
                "- Use clear, descriptive commit messages"
            ],
            tools=[
                ShellTools(),
                GithubTools(get_pull_requests=True, get_pull_request_changes=True),
                ReasoningTools(add_instructions=True, think=True, analyze=True)
            ]
        )

        # Create the coordinating team
        task_team = Team(
            name="task-implementation-team",
            mode="coordinate",
            members=[task_implementer, git_manager],
            model=AwsBedrock(id=model_id, session=session),
            instructions=[
                "Coordinate task implementation process with clear separation of tasks:",
                
                "PHASE 1 - IMPLEMENTATION (Task Implementer):",
                "   - Analyze the task requirements",
                "   - Set up repository and create branch",
                "   - Implement code changes to fulfill the task",
                "   - Write ONLY minimal code addressing the task",
                "   - Ensure code follows existing patterns",
                "   - Write appropriate tests",
                
                "PHASE 2 - GIT OPERATIONS (Git Manager):",
                "   - Wait for implementation completion",
                "   - Commit changes with clear messages",
                "   - Push feature branch to remote",
                "   - Provide branch information for manual PR creation",
                
                "COORDINATION RULES:",
                "- Each phase must complete before next begins",
                "- Share context and findings between agents",
                "- Maintain focus on minimal, targeted solutions",
                "- Ensure proper git workflow throughout",
                
                "TASK DETAILS:",
                f"Task ID: {task.id if task else 'N/A'}",
                f"Title: {task.title if task else 'N/A'}",
                f"Description: {task.description if task else 'N/A'}",
                
                "Chat history: " + system_prompt
            ],
            markdown=True,
            show_members_responses=True,
            enable_agentic_context=True,
            add_datetime_to_instructions=True,
            tools=[
                ShellTools(),
                FileTools(),
                GithubTools(get_pull_requests=True, get_pull_request_changes=True),
                ReasoningTools(add_instructions=True, think=True, analyze=True)
            ]
        )

        return task_team

    async def _process_issue(self, issue_url: str) -> str:
        """Process a GitHub issue to create PRD and tasks."""
        self._initialize_agents()
        
        # Extract repo URL from issue URL
        repo_match = re.search(r'(https://github\.com/[^/]+/[^/]+)/', issue_url)
        if repo_match:
            self.current_repo_url = repo_match.group(1)
        
        self.current_issue_url = issue_url
        
        # Create PRD from issue
        self.current_prd = await self.prd_agent.create_prd_from_issue(issue_url)
        
        # Create tasks from PRD
        self.current_tasks = await self.taskmaster.create_tasks_from_prd(self.current_prd)
        
        # Format response
        response = f"## Issue Processed Successfully\n\n"
        response += f"Issue URL: {issue_url}\n\n"
        response += f"### PRD Created\n\n"
        response += f"{self.current_prd[:500]}...\n\n"  # Show first 500 chars of PRD
        response += f"### Tasks Created\n\n"
        response += self.taskmaster.format_tasks_for_agents(self.current_tasks)
        response += f"\n\nYou can now use commands like:\n"
        response += f"- 'show task details for #1' to see details of a specific task\n"
        response += f"- 'implement task #1' to implement a specific task\n"
        response += f"- 'implement all tasks' to implement all tasks\n"
        
        return response

    async def _show_task_details(self, task_id: str) -> str:
        """Show details for a specific task."""
        self._initialize_agents()
        
        if not self.current_tasks:
            return "No tasks available. Please process an issue first."
        
        task_details = self.taskmaster.get_task_details(task_id)
        return f"## Task Details\n\n{task_details}"

    async def _show_implementation_details(self, task_id: str) -> str:
        """Show implementation details for a specific task."""
        self._initialize_agents()
        
        task = self.taskmaster.get_task_by_id(task_id)
        if not task:
            return f"Task with ID {task_id} not found."
        
        if not task.details:
            return f"No implementation details available for task {task_id}."
        
        return f"## Implementation Details for Task {task_id}\n\n{task.details}"

    async def _implement_task(self, task_id: str) -> str:
        """Implement a specific task."""
        self._initialize_agents()
        
        if not self.current_tasks:
            return "No tasks available. Please process an issue first."
        
        task = self.taskmaster.get_task_by_id(task_id)
        if not task:
            return f"Task with ID {task_id} not found."
        
        # Check if task dependencies are met
        available_tasks = self.taskmaster.get_available_tasks()
        if task not in available_tasks:
            return f"Task {task_id} has unmet dependencies. Please implement its dependencies first."
        
        # Create system prompt with task details
        system_prompt = f"""
        Implement the following task:
        
        Task ID: {task.id}
        Title: {task.title}
        Description: {task.description}
        Priority: {task.priority}
        
        Repository URL: {self.current_repo_url}
        Issue URL: {self.current_issue_url}
        
        PRD Context:
        {self.current_prd[:1000]}...
        """
        
        # Initialize team for task implementation
        team = self.initialize_team(system_prompt, task)
        
        # Run the team to implement the task
        response = team.run(
            f"Implement task #{task.id}: {task.title}",
            stream=False,
            stream_intermediate_steps=True,
            show_full_reasoning=True
        )
        
        # Update task status
        self.taskmaster.update_task_status(task_id, "done")
        
        return response.content

    async def _implement_all_tasks(self) -> str:
        """Implement all available tasks."""
        self._initialize_agents()
        
        if not self.current_tasks:
            return "No tasks available. Please process an issue first."
        
        available_tasks = self.taskmaster.get_available_tasks()
        if not available_tasks:
            return "No tasks available for implementation. All tasks may be completed or have unmet dependencies."
        
        response = "## Implementing All Available Tasks\n\n"
        
        for task in available_tasks:
            response += f"### Implementing Task {task.id}: {task.title}\n\n"
            task_response = await self._implement_task(task.id)
            response += f"{task_response}\n\n"
            
            # Refresh available tasks after each implementation
            available_tasks = self.taskmaster.get_available_tasks()
            if not available_tasks:
                break
        
        response += "## All Available Tasks Implemented\n\n"
        return response

    async def _list_tasks(self) -> str:
        """List all tasks."""
        self._initialize_agents()
        
        if not self.current_tasks:
            return "No tasks available. Please process an issue first."
        
        return f"## All Tasks\n\n{self.taskmaster.format_tasks_for_agents(self.current_tasks)}"

    async def _show_help(self) -> str:
        """Show help information."""
        help_text = """
        ## TaskPR Persona Help
        
        This persona helps you implement GitHub issues by breaking them down into tasks and implementing them.
        
        ### Available Commands:
        
        - **Process Issue**: Provide a GitHub issue URL to create a PRD and tasks
          Example: `https://github.com/username/repo/issues/1`
        
        - **List Tasks**: Show all available tasks
          Example: `list tasks`
        
        - **Show Task Details**: Show details for a specific task
          Example: `show task details for #1`
        
        - **Show Implementation Details**: Show implementation details for a specific task
          Example: `show implementation details for #1`
        
        - **Implement Task**: Implement a specific task
          Example: `implement task #1`
        
        - **Implement All Tasks**: Implement all available tasks
          Example: `implement all tasks`
        
        - **Help**: Show this help information
          Example: `help`
        """
        return help_text

    async def process_message(self, message: Message):
        """Process incoming messages and handle commands."""
        try:
            # Parse command from message
            command = self._parse_command(message.body)
            action = command["action"]
            
            # Execute appropriate action
            if action == "process_issue":
                response = await self._process_issue(command["issue_url"])
            elif action == "show_task_details":
                response = await self._show_task_details(command["task_id"])
            elif action == "show_implementation_details":
                response = await self._show_implementation_details(command["task_id"])
            elif action == "implement_task":
                response = await self._implement_task(command["task_id"])
            elif action == "implement_all_tasks":
                response = await self._implement_all_tasks()
            elif action == "list_tasks":
                response = await self._list_tasks()
            else:  # help or unknown command
                response = await self._show_help()
            
            # Stream response
            async def response_iterator():
                yield response
            
            await self.stream_message(response_iterator())
            
        except ValueError as e:
            error_message = f"Configuration Error: {str(e)}\nThis may be due to missing or invalid environment variables, model configuration, or input parameters."
            async def error_iterator():
                yield error_message
            await self.stream_message(error_iterator())
            
        except Exception as e:
            error_message = f"Error ({type(e).__name__}): {str(e)}\nAn unexpected error occurred while processing your request."
            async def error_iterator():
                yield error_message
            await self.stream_message(error_iterator())