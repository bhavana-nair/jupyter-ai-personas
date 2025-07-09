import asyncio
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_task_master import MCPTaskMaster

# Mock the MCP tools for testing
import json
from unittest.mock import patch

class MockTaskMasterMCP:
    def __init__(self):
        self.workflows = {}
        self.executions = {}
    
    def create_workflow(self, workflow_name: str, tasks: list) -> str:
        workflow_id = f"workflow_{len(self.workflows) + 1}"
        self.workflows[workflow_id] = {
            "name": workflow_name,
            "tasks": tasks,
            "status": "created"
        }
        return f"Workflow '{workflow_name}' created with ID: {workflow_id}"
    
    def execute_workflow(self, workflow_id: str, context: dict) -> str:
        if workflow_id not in self.workflows:
            return f"Workflow {workflow_id} not found"
        
        self.executions[workflow_id] = {
            "status": "running",
            "completed_tasks": [],
            "current_task": "fetch_pr",
            "context": context
        }
        return f"Started execution of workflow {workflow_id}"
    
    def get_status(self, workflow_id: str) -> dict:
        if workflow_id not in self.executions:
            return {"error": "Execution not found"}
        
        # Simulate progress
        execution = self.executions[workflow_id]
        if execution["current_task"] == "fetch_pr":
            execution["completed_tasks"] = ["fetch_pr"]
            execution["current_task"] = "analyze_ci"
        elif execution["current_task"] == "analyze_ci":
            execution["completed_tasks"] = ["fetch_pr", "analyze_ci"]
            execution["current_task"] = "review_code"
        
        return execution

# Mock MCP functions
mock_mcp = MockTaskMasterMCP()

def mock_create_task_workflow(workflow_name: str, tasks: list) -> str:
    return mock_mcp.create_workflow(workflow_name, tasks)

def mock_execute_task_workflow(workflow_id: str, context: dict) -> str:
    return mock_mcp.execute_workflow(workflow_id, context)

def mock_get_workflow_status(workflow_id: str) -> dict:
    return mock_mcp.get_status(workflow_id)

async def test_mcp_task_master():
    print("🧪 Testing MCP Task Master with Mock Server")
    print("=" * 50)
    
    # Patch the MCP tools with mocks
    with patch('mcp_task_master.create_task_workflow', side_effect=mock_create_task_workflow), \
         patch('mcp_task_master.execute_task_workflow', side_effect=mock_execute_task_workflow), \
         patch('mcp_task_master.get_workflow_status', side_effect=mock_get_workflow_status):
        
        try:
            # Initialize MCP Task Master
            mcp_master = MCPTaskMaster()
            
            # Test PR review
            pr_input = "https://github.com/bhavana-nair/jupyter-ai-personas/pull/6"
            
            print(f"📋 Starting MCP Task Master test for: {pr_input}")
            print("\n" + "-" * 40)
            
            result = await mcp_master.review_pr(pr_input)
            
            print("✅ MCP Task Master Results:")
            print("-" * 40)
            print(result)
            
            print("\n📊 Mock MCP Server State:")
            print(f"Workflows created: {len(mock_mcp.workflows)}")
            print(f"Executions started: {len(mock_mcp.executions)}")
            
            for wf_id, wf_data in mock_mcp.workflows.items():
                print(f"  - {wf_id}: {wf_data['name']} ({len(wf_data['tasks'])} tasks)")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp_task_master())