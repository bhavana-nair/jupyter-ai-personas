"""Task execution agent that picks up and executes tasks from TaskMaster."""

from agno.agent import Agent
from agno.models.aws import AwsBedrock
from agno.tools.shell import ShellTools
from agno.tools.file import FileTools
from agno.tools.python import PythonTools
from .taskmaster_client import TaskMasterClient, Task


class TaskExecutionAgent:
    """Agent that can pick up and execute specific tasks."""
    
    def __init__(self, model_id: str, session, agent_name: str = "task_executor"):
        self.taskmaster_client = TaskMasterClient()
        self.agent = Agent(
            name=agent_name,
            role="Task Execution Specialist",
            model=AwsBedrock(id=model_id, session=session),
            markdown=True,
            instructions=[
                "TASK EXECUTION WORKFLOW:",
                
                "STEP 1 - Task Selection:",
                "   - Review available tasks from TaskMaster",
                "   - Select tasks with no unmet dependencies",
                "   - Prioritize high-priority tasks",
                
                "STEP 2 - Task Analysis:",
                "   - Understand task requirements and acceptance criteria",
                "   - Identify required files and components",
                "   - Plan implementation approach",
                
                "STEP 3 - Implementation:",
                "   - Write minimal code to meet acceptance criteria",
                "   - Follow existing code patterns",
                "   - Implement proper error handling",
                
                "STEP 4 - Validation:",
                "   - Verify implementation meets acceptance criteria",
                "   - Test functionality where possible",
                "   - Document any assumptions or limitations",
                
                "EXECUTION PRINCIPLES:",
                "- Focus only on assigned task scope",
                "- Write minimal, clean code",
                "- Follow existing patterns and conventions",
                "- Complete acceptance criteria fully"
            ],
            tools=[
                ShellTools(),
                FileTools(),
                PythonTools()
            ]
        )
    
    async def execute_task(self, task: Task, repo_context: str = "") -> str:
        """Execute a specific task."""
        prompt = f"""
        Execute the following task:
        
        TASK: {task.title}
        ID: {task.id}
        PRIORITY: {task.priority}
        ESTIMATED EFFORT: {task.estimated_effort}
        
        DESCRIPTION:
        {task.description}
        
        DETAILS:
        {task.details or 'No additional details provided'}
        
        TEST STRATEGY:
        {task.test_strategy or 'No test strategy specified'}
        
        DEPENDENCIES: {', '.join(task.dependencies) if task.dependencies else 'None'}
        
        REPOSITORY CONTEXT:
        {repo_context}
        
        Implement this task following the execution workflow.
        Focus only on meeting the acceptance criteria with minimal code.
        
        IMPORTANT GIT INSTRUCTIONS:
        - If a feature branch is specified in the repository context, use that branch for implementation
        - Check if the branch exists before creating it (git branch --list <branch_name>)
        - If the branch exists, use it (git checkout <branch_name>)
        - If the branch doesn't exist, create it from main/master (git checkout -b <branch_name>)
        - Always commit your changes to the specified feature branch
        - Push changes to the same branch name on remote
        """
        
        response = self.agent.run(prompt, stream=False)
        return response.content if hasattr(response, 'content') else str(response)
    
    def get_available_tasks(self) -> list[Task]:
        """Get tasks that this agent can execute."""
        return self.taskmaster_client.get_available_tasks()
    
    def mark_task_complete(self, task_id: str) -> bool:
        """Mark a task as completed in TaskMaster."""
        return self.taskmaster_client.update_task_status(task_id, 'done')
    
    def mark_task_in_progress(self, task_id: str) -> bool:
        """Mark a task as in progress in TaskMaster."""
        return self.taskmaster_client.update_task_status(task_id, 'in-progress')