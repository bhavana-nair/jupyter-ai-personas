#!/usr/bin/env python3
"""Test with alternative model format."""

import os
import json
import subprocess

def test_alt_model():
    """Test TaskMaster with alternative model format."""
    print("=== Testing with Alternative Model Format ===")
    
    # Check environment variable
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set")
        return False
    
    # Create config directory
    work_dir = os.getcwd()
    config_dir = os.path.join(work_dir, ".taskmaster")
    os.makedirs(config_dir, exist_ok=True)
    
    # Create config file with alternative model format
    config_path = os.path.join(config_dir, "config.json")
    config = {
        "provider": "anthropic",
        "model": "claude-3-sonnet-20240229",
        "apiKey": api_key
    }
    
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"Created config at {config_path}")
    
    # Create a simple PRD
    prd_content = "Create a simple calculator app."
    
    prd_path = os.path.join(work_dir, "simple_prd.txt")
    with open(prd_path, "w") as f:
        f.write(prd_content)
    
    # Run TaskMaster directly
    print("\nRunning TaskMaster...")
    cmd = ["npx", "task-master", "parse-prd", "--input", prd_path, "--force"]
    print(f"Running command: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print(f"Return code: {result.returncode}")
    print(f"STDOUT: {result.stdout}")
    print(f"STDERR: {result.stderr}")
    
    return result.returncode == 0

if __name__ == "__main__":
    success = test_alt_model()
    print(f"\nTest {'succeeded' if success else 'failed'}")