#!/usr/bin/env python3
"""Test script for PR Creation Persona with TaskMaster integration."""

import asyncio
import os
import sys
from unittest.mock import MagicMock

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

class MockMessage:
    """Mock message for testing."""
    def __init__(self, body):
        self.body = body

class MockConfig:
    """Mock config for testing."""
    def __init__(self):
        self.lm_provider = MagicMock()
        self.lm_provider.name = "test-provider"
        self.lm_provider_params = {"model_id": "anthropic.claude-3-5-sonnet-20240620-v1"}

class MockYChat:
    """Mock YChat for testing."""
    def __init__(self):
        self.add_message = MagicMock()
        self.awareness = None

async def test_pr_creation_persona():
    """Test the PR Creation Persona with TaskMaster integration."""
    print("=== Testing PR Creation Persona with TaskMaster ===")
    
    try:
        # Import the persona
        from jupyter_ai_personas.pr_creation_persona.persona import PRCreationPersona
        
        # Create a mock persona
        ychat = MockYChat()
        config_manager = MockConfig()
        message_interrupted = MagicMock()
        
        # Create the persona with required arguments
        persona = PRCreationPersona(
            ychat=ychat,
            config_manager=config_manager,
            message_interrupted=message_interrupted
        )
        persona.stream_message = MagicMock()
        
        # Test command parsing
        print("\nTesting command parsing...")
        
        # Test issue URL parsing
        command = persona._parse_command("https://github.com/username/repo/issues/123")
        print(f"Issue URL command: {command}")
        assert command["action"] == "process_issue"
        
        # Test task details parsing
        command = persona._parse_command("show task details for #1")
        print(f"Task details command: {command}")
        assert command["action"] == "show_task_details"
        
        # Test implement task parsing
        command = persona._parse_command("implement task #2")
        print(f"Implement task command: {command}")
        assert command["action"] == "implement_task"
        
        # Test list tasks parsing
        command = persona._parse_command("list tasks")
        print(f"List tasks command: {command}")
        assert command["action"] == "list_tasks"
        
        # Test standard PR creation parsing
        command = persona._parse_command("Fix the bug in the authentication module")
        print(f"Standard PR creation command: {command}")
        assert command["action"] == "standard_pr_creation"
        
        print("\nCommand parsing tests passed!")
        
        # Mock TaskMaster and PRD agent
        persona.taskmaster = MagicMock()
        persona.prd_agent = MagicMock()
        
        # Mock current state
        persona.current_repo_url = "https://github.com/username/repo"
        persona.current_issue_url = "https://github.com/username/repo/issues/123"
        persona.current_prd = "# Test PRD\n\nThis is a test PRD."
        persona.current_tasks = [
            MagicMock(id="1", title="Test Task 1", description="Description 1", priority="high", status="pending", dependencies=[]),
            MagicMock(id="2", title="Test Task 2", description="Description 2", priority="medium", status="pending", dependencies=["1"])
        ]
        
        # Mock taskmaster methods
        persona.taskmaster.get_task_by_id.return_value = persona.current_tasks[0]
        persona.taskmaster.get_available_tasks.return_value = [persona.current_tasks[0]]
        persona.taskmaster.get_task_details.return_value = "Task details for task 1"
        persona.taskmaster.format_tasks_for_agents.return_value = "Task 1\nTask 2"
        
        # Test list tasks
        print("\nTesting list tasks...")
        message = MockMessage("list tasks")
        await persona.process_message(message)
        persona.stream_message.assert_called_once()
        persona.stream_message.reset_mock()
        
        # Test show task details
        print("\nTesting show task details...")
        message = MockMessage("show task details for #1")
        await persona.process_message(message)
        persona.taskmaster.get_task_details.assert_called_once_with("1")
        persona.stream_message.assert_called_once()
        persona.stream_message.reset_mock()
        
        print("\nAll tests passed!")
        return True
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_pr_creation_persona())
    print(f"\nTest {'succeeded' if success else 'failed'}")