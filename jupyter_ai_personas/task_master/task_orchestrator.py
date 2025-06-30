from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import asyncio
from agno.agent import Agent

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
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0

class TaskOrchestrator:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.execution_order: List[str] = []
        self.shared_context: Dict[str, Any] = {}
    
    def add_task(self, task: Task):
        self.tasks[task.id] = task
        self._update_execution_order()
    
    def _update_execution_order(self):
        """Simple topological sort for task dependencies"""
        visited = set()
        temp_visited = set()
        order = []
        
        def visit(task_id):
            if task_id in temp_visited:
                raise ValueError(f"Circular dependency detected involving task {task_id}")
            if task_id in visited:
                return
            
            temp_visited.add(task_id)
            task = self.tasks[task_id]
            for dep in task.dependencies:
                if dep in self.tasks:
                    visit(dep)
            temp_visited.remove(task_id)
            visited.add(task_id)
            order.append(task_id)
        
        for task_id in self.tasks:
            if task_id not in visited:
                visit(task_id)
        
        # Sort by priority within dependency constraints
        self.execution_order = sorted(order, key=lambda x: -self.tasks[x].priority)
    
    async def execute_task(self, task_id: str) -> Any:
        task = self.tasks[task_id]
        
        # Check dependencies
        for dep_id in task.dependencies:
            if dep_id in self.tasks and self.tasks[dep_id].status != TaskStatus.COMPLETED:
                task.status = TaskStatus.SKIPPED
                return None
        
        task.status = TaskStatus.RUNNING
        
        try:
            # Merge shared context with task context
            full_context = {**self.shared_context, **task.context}
            
            # For comment creation task, include analysis results
            if task_id == "create_comments":
                analysis_summary = "\n\nAnalysis Results:\n"
                for dep_id in task.dependencies:
                    if f"{dep_id}_result" in self.shared_context:
                        analysis_summary += f"\n{dep_id.upper()}:\n{self.shared_context[f'{dep_id}_result']}\n"
                input_text = full_context.get('input', '') + analysis_summary
            else:
                input_text = full_context.get('input', '')
            
            print(f"[DEBUG] Executing task {task_id} with input: {input_text[:100]}...")
            
            result = await task.agent.arun(input_text)
            
            # Extract content from RunResponse
            if hasattr(result, 'content'):
                content = result.content
            else:
                content = str(result)
            
            print(f"[DEBUG] Task {task_id} result type: {type(result)}, content length: {len(content) if content else 0}")
            
            task.result = content
            task.status = TaskStatus.COMPLETED
            
            # Update shared context with results
            self.shared_context[f"{task.id}_result"] = content
            
            return content
            
        except Exception as e:
            print(f"[DEBUG] Task {task_id} failed: {str(e)}")
            task.error = str(e)
            task.status = TaskStatus.FAILED
            return None
    
    async def execute_all(self) -> Dict[str, Any]:
        results = {}
        
        for task_id in self.execution_order:
            task = self.tasks[task_id]
            if task.status == TaskStatus.PENDING:
                result = await self.execute_task(task_id)
                results[task_id] = result
        
        return results
    
    def get_task_status(self) -> Dict[str, TaskStatus]:
        return {task_id: task.status for task_id, task in self.tasks.items()}