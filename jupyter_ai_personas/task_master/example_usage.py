"""Example usage of TaskMaster integration with PR Creation Persona."""

import asyncio
from taskmaster_client import TaskMasterClient
from prd_agent import PRDAgent
from task_agent import TaskExecutionAgent


async def example_workflow():
    """Example workflow showing TaskMaster integration."""
    
    # Sample issue description
    issue_description = """
    Implement user authentication system for the web application.
    
    Requirements:
    - User registration and login
    - Password hashing and validation
    - Session management
    - JWT token authentication
    - Password reset functionality
    - Email verification
    
    The system should be secure and follow best practices.
    """
    
    # Initialize components
    project_root = "/path/to/your/project"
    taskmaster_client = TaskMasterClient(project_root)
    
    # Create PRD from issue (would use actual model in real scenario)
    print("Creating PRD from issue...")
    prd_content = f"""
    Product Requirements Document: User Authentication System
    
    Problem Statement:
    The application needs a secure user authentication system to manage user access and sessions.
    
    Solution Overview:
    Implement a comprehensive authentication system with registration, login, and session management.
    
    Functional Requirements:
    - User registration with email verification
    - Secure login with password validation
    - JWT-based session management
    - Password reset functionality
    - Account security features
    
    Technical Requirements:
    - Password hashing using bcrypt
    - JWT token generation and validation
    - Email service integration
    - Database schema for user management
    - API endpoints for authentication
    
    Acceptance Criteria:
    - Users can register with email verification
    - Users can login securely
    - Sessions are managed with JWT tokens
    - Password reset works via email
    - All security best practices are followed
    """
    
    # Generate tasks using TaskMaster
    print("Generating tasks using TaskMaster...")
    tasks = await taskmaster_client.create_tasks_from_prd(prd_content)
    
    print(f"Generated {len(tasks)} tasks:")
    for task in tasks:
        print(f"- {task.title} (Priority: {task.priority})")
    
    # Get available tasks for agents
    available_tasks = taskmaster_client.get_available_tasks()
    print(f"\nAvailable tasks for agents: {len(available_tasks)}")
    
    # Format tasks for agents
    formatted_tasks = taskmaster_client.format_tasks_for_agents(available_tasks)
    print("\nFormatted tasks:")
    print(formatted_tasks)
    
    # Example of agent picking up a task
    if available_tasks:
        task_agent = TaskExecutionAgent("claude-3-sonnet", None, "auth_implementer")
        
        first_task = available_tasks[0]
        print(f"\nAgent picking up task: {first_task.title}")
        
        # Mark task as in progress
        task_agent.mark_task_in_progress(first_task.id)
        
        # Execute task (would involve actual implementation)
        print("Executing task...")
        # result = await task_agent.execute_task(first_task, repo_context)
        
        # Mark task as complete
        task_agent.mark_task_complete(first_task.id)
        print("Task completed!")


if __name__ == "__main__":
    asyncio.run(example_workflow())