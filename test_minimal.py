#!/usr/bin/env python3
"""Minimal test for TaskMaster."""

import os
import json
import subprocess
import asyncio

async def test_minimal():
    """Run a minimal test directly using subprocess."""
    print("=== Minimal TaskMaster Test ===")
    
    # Check environment variable
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set")
        return False
    print(f"API key found: {api_key[:8]}...{api_key[-4:]}")
    
    # Create config directory
    work_dir = os.getcwd()
    config_dir = os.path.join(work_dir, ".taskmaster")
    os.makedirs(config_dir, exist_ok=True)
    
    # Create config file
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
    prd_content = "Create a simple calculator app."
    
    prd_path = os.path.join(work_dir, "minimal_prd.txt")
    with open(prd_path, "w") as f:
        f.write(prd_content)
    
    # Run TaskMaster directly
    print("\nRunning TaskMaster directly...")
    try:
        # Create environment with API key
        env = os.environ.copy()
        
        cmd = ["npx", "task-master", "parse-prd", "--input", prd_path, "--force"]
        print(f"Running command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        
        print(f"Return code: {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        
        if result.returncode != 0:
            print("Command failed")
            return False
            
        # Check if tasks.json was created
        tasks_path = os.path.join(work_dir, "tasks.json")
        if os.path.exists(tasks_path):
            print(f"\nTasks file created at {tasks_path}")
            with open(tasks_path, "r") as f:
                tasks_data = json.load(f)
            print(f"Tasks data: {json.dumps(tasks_data, indent=2)}")
            return True
        else:
            alt_path = os.path.join(work_dir, ".taskmaster", "tasks", "tasks.json")
            if os.path.exists(alt_path):
                print(f"\nTasks file created at {alt_path}")
                with open(alt_path, "r") as f:
                    tasks_data = json.load(f)
                print(f"Tasks data: {json.dumps(tasks_data, indent=2)}")
                return True
            else:
                print("\nNo tasks file was created")
                return False
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_minimal())
    print(f"\nTest {'succeeded' if success else 'failed'}")