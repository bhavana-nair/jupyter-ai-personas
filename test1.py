#!/usr/bin/env python3
"""Test script for TaskMasterClient."""

import asyncio
import sys
import os
import json
import subprocess

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from jupyter_ai_personas.task_master.taskmaster_client import TaskMasterClient

async def test_taskmaster_client():
    """Test the TaskMasterClient class."""
    print("=== Testing TaskMasterClient ===")
    
    # Check environment variable
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set")
        return False
    print(f"API key found: {api_key[:8]}...{api_key[-4:]}")
    
    # Check if config directory exists
    work_dir = os.getcwd()
    config_dir = os.path.join(work_dir, ".taskmaster")
    config_path = os.path.join(config_dir, "config.json")
    
    if os.path.exists(config_path):
        print(f"Config file exists at {config_path}")
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            print(f"Config contents: {json.dumps(config, indent=2)}")
        except Exception as e:
            print(f"Error reading config: {e}")
    else:
        print(f"Config file does not exist at {config_path}")
    
    # Check if npx and task-master are available
    try:
        print("\nChecking npx and task-master...")
        subprocess.run(['npx', '--version'], check=True, capture_output=True)
        version_result = subprocess.run(['npx', 'task-master', '--version'], 
                                     capture_output=True, text=True)
        print(f"task-master version: {version_result.stdout.strip() if version_result.returncode == 0 else 'not available'}")
    except Exception as e:
        print(f"Error checking tools: {e}")
    
    # Create a TaskMasterClient instance
    print("\nCreating TaskMasterClient...")
    client = TaskMasterClient()
    print("TaskMasterClient created")
    
    # Create a sample PRD
    prd_content = """
    # Product Requirements Document
    
    ## Problem Statement
    Need to implement a user authentication system for our web application.
    
    ## Solution Overview
    Create a secure authentication system with login/logout functionality.
    
    ## Requirements
    - User registration with email verification
    - Login with email and password
    - Password reset functionality
    - Session management with JWT tokens
    - Role-based access control
    """
    
    try:
        # Generate tasks from PRD
        print("\nGenerating tasks from PRD...")
        tasks = await client.create_tasks_from_prd(prd_content)
        
        print(f"Generated {len(tasks)} tasks:")
        for i, task in enumerate(tasks):
            print(f"\nTask {i+1}:")
            print(f"  ID: {task.id}")
            print(f"  Title: {task.title}")
            print(f"  Description: {task.description}")
            print(f"  Priority: {task.priority}")
        
        # Get available tasks
        available_tasks = client.get_available_tasks()
        print(f"\nAvailable tasks: {len(available_tasks)}")
        
        # Format tasks for agents
        formatted = client.format_tasks_for_agents(available_tasks)
        print("\nFormatted tasks for agents:")
        print(formatted)
        
        return True
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_taskmaster_client())
    print(f"\nTest {'succeeded' if success else 'failed'}")