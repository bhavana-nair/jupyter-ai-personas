"""TaskMaster AI client integration using the actual TaskMaster library."""

import os
import json
import tempfile
import subprocess
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class Task:
    """Represents a task from TaskMaster."""
    id: str
    title: str
    description: str
    priority: str
    status: str
    dependencies: List[str]
    details: Optional[str] = None
    test_strategy: Optional[str] = None


class TaskMasterClient:
    """Client for integrating with actual TaskMaster AI."""
    
    def __init__(self, project_root: str = None):
        # Use a persistent directory for TaskMaster
        if project_root:
            self.project_root = project_root
        else:
            home_dir = os.path.expanduser("~")
            self.project_root = os.path.join(home_dir, ".jupyter-ai-taskmaster")
            os.makedirs(self.project_root, exist_ok=True)
            
        self.tasks: List[Task] = []
        self._taskmaster_available = True
        self._ensure_taskmaster_setup()
    
    def _ensure_taskmaster_setup(self):
        """Check if TaskMaster is available and set up config."""
        try:
            # Check if npx is available
            print("Checking npx availability...")
            subprocess.run(['npx', '--version'], capture_output=True, check=True)
            print("npx is available")
            
            # Check if task-master is available
            print("Checking task-master availability...")
            version_result = subprocess.run(['npx', 'task-master', '--version'], 
                                         capture_output=True, text=True)
            print(f"task-master version: {version_result.stdout.strip() if version_result.returncode == 0 else 'not available'}")
            if version_result.returncode != 0:
                print(f"task-master check failed: {version_result.stderr}")
                self._taskmaster_available = False
                return
            
            # Create config directory with API key
            work_dir = os.getcwd()
            config_dir = os.path.join(work_dir, ".taskmaster")
            os.makedirs(config_dir, exist_ok=True)
            
            # Use the provided Claude API key with proper format
            api_key = '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'
            # Set environment variable for other components that might need it
            os.environ['ANTHROPIC_API_KEY'] = api_key
            
            # Create config file with Anthropic API
            config_path = os.path.join(config_dir, "config.json")
            with open(config_path, "w") as f:
                # Create config with all possible key formats that TaskMaster might use
                json.dump({
                    "provider": "anthropic",
                    "model": "claude-3-5-sonnet-20241022",
                    "apiKey": api_key
                }, f, indent=2)
            print("Using Anthropic API for TaskMaster")
                
            print(f"Created TaskMaster config at {config_path}")
            self._taskmaster_available = True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"Warning: TaskMaster not available or timed out: {e}")
            self._taskmaster_available = False
        except ValueError as e:
            print(f"Configuration error: {e}")
            self._taskmaster_available = False
    
    async def create_tasks_from_prd(self, prd_content: str) -> List[Task]:
        """Create tasks from PRD using TaskMaster with Claude API."""
        if not self._taskmaster_available:
            raise ValueError("TaskMaster is not available. Please install it with 'npm install -g task-master'.")
            
        # Ensure TaskMaster is available
        if not self._taskmaster_available:
            self._ensure_taskmaster_setup()
            if not self._taskmaster_available:
                raise ValueError("TaskMaster is not available. Please install it with 'npm install -g task-master'.")
            
        try:
            # Use current directory where TaskMaster is already installed
            work_dir = os.getcwd()
            print(f"Using current directory for TaskMaster: {work_dir}")
            
            # Create PRD file
            prd_path = os.path.join(work_dir, 'prd.txt')
            with open(prd_path, 'w') as f:
                f.write(prd_content)
            
            # Use TaskMaster to parse PRD and generate tasks
            print(f"Running TaskMaster parse-prd on {prd_path}...")
            print(f"Command: npx task-master parse-prd --input {prd_path} --force")
            print(f"Working directory: {work_dir}")
            try:
                # Run parse-prd in the current directory
                result = subprocess.run([
                    'npx', 'task-master', 'parse-prd', 
                    '--input', prd_path,
                    '--force'
                ], cwd=work_dir, capture_output=True, text=True)
                print(f"Command completed with return code: {result.returncode}")
            except Exception as cmd_error:
                print(f"Command execution error: {cmd_error}")
                raise ValueError(f"Failed to execute TaskMaster command: {cmd_error}")
            
            print(f"TaskMaster parse-prd result: {result.returncode}")
            if result.returncode != 0:
                print(f"TaskMaster stderr: {result.stderr}")
                print(f"TaskMaster stdout: {result.stdout}")
                # Try running with --debug flag to get more information
                debug_result = subprocess.run([
                    'npx', 'task-master', 'parse-prd', 
                    '--input', prd_path,
                    '--force',
                    '--debug'
                ], cwd=work_dir, capture_output=True, text=True)
                print(f"Debug output: {debug_result.stdout}")
                print(f"Debug errors: {debug_result.stderr}")
                raise ValueError(f"TaskMaster failed to parse PRD: {result.stderr}")
            
            try:
                return self._load_tasks()
            except Exception as load_error:
                print(f"Error loading tasks: {load_error}")
                raise ValueError(f"Failed to load tasks: {load_error}")
                
        except Exception as e:
            print(f"Error creating tasks: {e}")
            raise ValueError(f"Failed to create tasks: {e}")
    
    def _load_tasks(self) -> List[Task]:
        """Load tasks from TaskMaster tasks.json file."""
        # Look for tasks.json in various possible locations
        work_dir = os.getcwd()
        possible_paths = [
            os.path.join(work_dir, "tasks.json"),
            os.path.join(work_dir, ".taskmaster", "tasks", "tasks.json")
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                tasks_path = path
                print(f"Found tasks at: {tasks_path}")
                break
        else:
            print("Tasks file not found")
            return []
        
        if not os.path.exists(tasks_path):
            return []
        
        try:
            with open(tasks_path, 'r') as f:
                data = json.load(f)
            
            tasks = []
            # Check if tasks are nested under 'master' key
            if 'master' in data and 'tasks' in data['master']:
                task_list = data['master']['tasks']
            else:
                task_list = data.get('tasks', [])
                
            for task_data in task_list:
                task = Task(
                    id=str(task_data.get('id', '')),  # Convert ID to string
                    title=task_data.get('title', ''),
                    description=task_data.get('description', ''),
                    priority=task_data.get('priority', 'medium'),
                    status=task_data.get('status', 'pending'),
                    dependencies=[str(dep) for dep in task_data.get('dependencies', [])],  # Convert dependencies to strings
                    details=task_data.get('details'),
                    test_strategy=task_data.get('testStrategy')
                )
                tasks.append(task)
            
            self.tasks = tasks
            return tasks
            
        except Exception as e:
            print(f"Error loading tasks: {e}")
            return []
    
    def get_available_tasks(self) -> List[Task]:
        """Get tasks that can be worked on (no unmet dependencies)."""
        completed_tasks = {t.id for t in self.tasks if t.status == 'done'}
        
        available = []
        for task in self.tasks:
            if task.status == 'pending':
                if not task.dependencies or all(dep in completed_tasks for dep in task.dependencies):
                    available.append(task)
        
        return available
    
    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """Get a task by its ID."""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None
    
    def update_task_status(self, task_id: str, status: str) -> bool:
        """Update the status of a task."""
        task = self.get_task_by_id(task_id)
        if not task:
            return False
        
        task.status = status
        
        # Try to update status using TaskMaster CLI if available
        try:
            result = subprocess.run([
                'npx', 'task-master', 'set-status',
                f'--to-{status}',
                '--id', task_id
            ], cwd=self.project_root, capture_output=True, text=True)
        except Exception:
            # Ignore CLI errors, we've already updated the in-memory task
            pass
            
        return True
    
    def format_tasks_for_agents(self, tasks: List[Task] = None) -> str:
        """Format tasks in a way that's easy for agents to understand."""
        if tasks is None:
            tasks = self.tasks
            
        if not tasks:
            return "No tasks available."
        
        formatted = ""
        for task in tasks:
            formatted += f"- Task #{task.id}: {task.title} (Priority: {task.priority}, Status: {task.status})\n"
            if task.dependencies:
                formatted += f"  Dependencies: {', '.join(['#' + dep for dep in task.dependencies])}\n"
        
        return formatted
    
    def get_task_details(self, task_id: str) -> str:
        """Get formatted details for a specific task."""
        task = self.get_task_by_id(task_id)
        if not task:
            return f"Task with ID {task_id} not found."
        
        details = f"## Task {task.id}: {task.title}\n\n"
        details += f"**Priority:** {task.priority}\n\n"
        details += f"**Status:** {task.status}\n\n"
        
        if task.dependencies:
            details += f"**Dependencies:** {', '.join(task.dependencies)}\n\n"
        
        details += f"**Description:**\n{task.description}\n\n"
        
        if task.details:
            details += f"**Additional Details:**\n{task.details}\n\n"
            
        if task.test_strategy:
            details += f"**Test Strategy:**\n{task.test_strategy}\n\n"
            
        return details