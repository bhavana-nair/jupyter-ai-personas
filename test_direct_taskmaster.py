#!/usr/bin/env python3
"""Direct test of TaskMaster CLI."""

import os
import subprocess
import json

def test_taskmaster_direct():
    """Test TaskMaster CLI directly."""
    print("=== Testing TaskMaster CLI Directly ===")
    
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
        "apiKey": api_key,
        "headers": {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
    }
    
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"Created config at {config_path}")
    
    # Create a simple PRD file
    prd_content = """
    # Product Requirements Document
    
    ## Problem Statement
    Need a simple calculator app.
    
    ## Solution Overview
    Create a basic calculator with add/subtract functions.
    
    ## Requirements
    - Addition function
    - Subtraction function
    """
    
    prd_path = os.path.join(work_dir, "simple_prd.txt")
    with open(prd_path, "w") as f:
        f.write(prd_content)
    print(f"Created PRD at {prd_path}")
    
    # Run TaskMaster directly
    print("\nRunning TaskMaster directly...")
    try:
        # Ensure environment variable is set for subprocess
        env = os.environ.copy()
        
        # Run with debug flag
        cmd = ["npx", "task-master", "parse-prd", "--input", prd_path, "--force"]
        print(f"Running command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        
        print(f"Return code: {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        
        # Check if tasks.json was created
        tasks_path = os.path.join(work_dir, "tasks.json")
        if os.path.exists(tasks_path):
            print(f"\nTasks file created at {tasks_path}")
            with open(tasks_path, "r") as f:
                tasks_data = json.load(f)
            print(f"Tasks data: {json.dumps(tasks_data, indent=2)}")
            return True
        else:
            print("\nTasks file was not created")
            return False
            
    except Exception as e:
        print(f"Error running TaskMaster: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_taskmaster_direct()
    print(f"\nTest {'succeeded' if success else 'failed'}")