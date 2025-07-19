#!/usr/bin/env python3
"""Simplified test for TaskMasterClient."""

import asyncio
import sys
import os
import json
import subprocess

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from jupyter_ai_personas.task_master.taskmaster_client import TaskMasterClient

async def test_simple():
    """Simple test focusing only on the core functionality."""
    print("=== Simple TaskMaster Test ===")
    
    # Check environment variable
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set")
        return False
    print(f"API key found: {api_key[:8]}...{api_key[-4:]}")
    
    # Create config directory and file directly
    work_dir = os.getcwd()
    config_dir = os.path.join(work_dir, ".taskmaster")
    os.makedirs(config_dir, exist_ok=True)
    
    config_path = os.path.join(config_dir, "config.json")
    config = {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "apiKey": api_key
    }
    
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"Created config at {config_path}")
    
    # Create a very simple PRD
    prd_content = """
    # Simple Calculator
    
    Create a basic calculator app with addition and subtraction.
    """
    
    prd_path = os.path.join(work_dir, "simple_prd.txt")
    with open(prd_path, "w") as f:
        f.write(prd_content)
    
    # Run TaskMaster directly
    print("\nRunning TaskMaster directly...")
    try:
        cmd = ["npx", "task-master", "parse-prd", "--input", prd_path, "--force"]
        print(f"Running command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        print(f"Return code: {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        
        if result.returncode != 0:
            print("Direct command failed")
            return False
            
        print("\nDirect command succeeded, now trying through client...")
        
        # Now try through the client
        client = TaskMasterClient()
        tasks = await client.create_tasks_from_prd("Create a simple calculator app.")
        
        print(f"Generated {len(tasks)} tasks")
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_simple())
    print(f"\nTest {'succeeded' if success else 'failed'}")