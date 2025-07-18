#!/usr/bin/env python3
"""Test script for PR Creation Persona command parsing."""

import re

def parse_command(message: str):
    """Parse user command to determine if it's a task-related command."""
    # Check for issue URL
    issue_match = re.search(r'(https://github\.com/[^/\s]+/[^/\s]+/issues/\d+)', message)
    if issue_match:
        return {
            "action": "process_issue",
            "issue_url": issue_match.group(1)
        }
        
    # Check for task details command
    task_details_match = re.search(r'(?:show|get|display)\s+task\s+(?:details|info)?\s+(?:for|of)?\s*[#]?(\d+)', message, re.IGNORECASE)
    if task_details_match:
        return {
            "action": "show_task_details",
            "task_id": task_details_match.group(1)
        }
        
    # Check for implement task command
    impl_task_match = re.search(r'implement\s+task\s*[#]?(\d+)', message, re.IGNORECASE)
    if impl_task_match:
        return {
            "action": "implement_task",
            "task_id": impl_task_match.group(1)
        }
        
    # Check for list tasks command
    if re.search(r'(?:list|show|get)\s+(?:all\s+)?tasks', message, re.IGNORECASE):
        return {
            "action": "list_tasks"
        }
        
    # Default to standard PR creation
    return {
        "action": "standard_pr_creation"
    }

def test_command_parsing():
    """Test the command parsing functionality."""
    print("=== Testing Command Parsing ===")
    
    # Test issue URL parsing
    command = parse_command("https://github.com/username/repo/issues/123")
    print(f"Issue URL command: {command}")
    assert command["action"] == "process_issue"
    assert command["issue_url"] == "https://github.com/username/repo/issues/123"
    
    # Test task details parsing
    command = parse_command("show task details for #1")
    print(f"Task details command: {command}")
    assert command["action"] == "show_task_details"
    assert command["task_id"] == "1"
    
    # Test implement task parsing
    command = parse_command("implement task #2")
    print(f"Implement task command: {command}")
    assert command["action"] == "implement_task"
    assert command["task_id"] == "2"
    
    # Test list tasks parsing
    command = parse_command("list tasks")
    print(f"List tasks command: {command}")
    assert command["action"] == "list_tasks"
    
    # Test standard PR creation parsing
    command = parse_command("Fix the bug in the authentication module")
    print(f"Standard PR creation command: {command}")
    assert command["action"] == "standard_pr_creation"
    
    print("\nAll command parsing tests passed!")
    return True

if __name__ == "__main__":
    success = test_command_parsing()
    print(f"\nTest {'succeeded' if success else 'failed'}")