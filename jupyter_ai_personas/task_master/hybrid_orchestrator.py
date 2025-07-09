from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum
import asyncio
from agno.agent import Agent
from agno.models.google import Gemini

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class Task:
    id: str
    name: str
    agent: Agent
    dependencies: List[str]
    priority: int = 0
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    skip_condition: Optional[str] = None  # LLM-evaluated condition

class HybridOrchestrator:
    def __init__(self, model):
        self.tasks: Dict[str, Task] = {}
        self.shared_context: Dict[str, Any] = {}
        self.coordinator_llm = Agent(
            name="coordinator",
            role="Workflow Coordinator", 
            model=model,
            instructions=[
                "You are a workflow coordinator for PR reviews.",
                "Analyze the context and decide whether to skip tasks based on efficiency.",
                "Return ONLY 'SKIP' or 'EXECUTE' for each task decision.",
                "Skip tasks when:",
                "- CI is already passing (skip detailed CI analysis)",
                "- PR is very small (skip security scan)",
                "- No code changes (skip code review)",
                "- Documentation-only changes (skip security scan)"
            ]
        )
    
    def add_task(self, task: Task):
        self.tasks[task.id] = task
    
    async def should_execute_task(self, task_id: str) -> bool:
        """Use LLM to decide if task should be executed"""
        task = self.tasks[task_id]
        
        if not task.skip_condition:
            return True  # Always execute if no skip condition
        
        # Simple rule-based decisions to avoid LLM loops
        context_str = str(self.shared_context.get('fetch_pr_result', ''))
        
        # Rule-based skip logic
        if 'analyze_ci' in task_id:
            if 'CI is passing' in context_str or 'all checks passed' in context_str.lower():
                print(f"[COORDINATOR] {task_id}: SKIP (CI already passing)")
                return False
        
        elif 'review_code' in task_id:
            if '.md' in context_str and '.py' not in context_str:
                print(f"[COORDINATOR] {task_id}: SKIP (documentation only)")
                return False
        
        elif 'scan_security' in task_id:
            if 'small PR' in context_str or len(context_str) < 500:
                print(f"[COORDINATOR] {task_id}: SKIP (small PR)")
                return False
        
        print(f"[COORDINATOR] {task_id}: EXECUTE")
        return True
    
    async def execute_task(self, task_id: str) -> Any:
        task = self.tasks[task_id]
        
        # Check if LLM says to skip this task
        if not await self.should_execute_task(task_id):
            task.status = TaskStatus.SKIPPED
            return f"Skipped by coordinator: {task.skip_condition}"
        
        # Check dependencies
        for dep_id in task.dependencies:
            if dep_id in self.tasks and self.tasks[dep_id].status not in [TaskStatus.COMPLETED, TaskStatus.SKIPPED]:
                task.status = TaskStatus.SKIPPED
                return None
        
        task.status = TaskStatus.RUNNING
        
        try:
            # Execute with shared context
            input_text = self.shared_context.get('input', '')
            
            # Add relevant context from completed tasks
            if task_id == "create_comments":
                analysis_context = "\n\nAnalysis Results for Comment Creation:\n"
                for dep_id in task.dependencies:
                    if f"{dep_id}_result" in self.shared_context:
                        result_content = self.shared_context[f'{dep_id}_result']
                        analysis_context += f"\n=== {dep_id.upper()} FINDINGS ===\n{result_content}\n"
                
                input_text += analysis_context
                input_text += "\n\nBased on the above analysis, create multiple specific inline comments on the changed files."
            
            result = await task.agent.arun(input_text)
            content = result.content if hasattr(result, 'content') else str(result)
            
            task.result = content
            task.status = TaskStatus.COMPLETED
            self.shared_context[f"{task.id}_result"] = content
            
            return content
            
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED
            return None
    
    async def execute_workflow(self, input_text: str) -> Dict[str, Any]:
        """Execute workflow with intelligent decisions"""
        self.shared_context['input'] = input_text
        results = {}
        
        # Define execution order
        execution_order = ["fetch_pr", "analyze_ci", "review_code", "scan_security", "create_comments"]
        
        for task_id in execution_order:
            if task_id in self.tasks:
                print(f"\n[WORKFLOW] Starting task: {task_id}")
                result = await self.execute_task(task_id)
                results[task_id] = result
                print(f"[WORKFLOW] Completed task: {task_id}")
        
        return {
            'status': {task_id: task.status for task_id, task in self.tasks.items()},
            'results': results
        }