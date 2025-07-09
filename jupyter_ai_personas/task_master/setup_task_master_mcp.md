# Task Master MCP Setup Guide

## Step 1: Install Task Master MCP Server

```bash
# Install Task Master CLI
npm install -g @task-master/cli

# Or using Docker
docker pull taskmaster/mcp-server
```

## Step 2: Configure MCP Server

Create `task-master-config.json`:
```json
{
  "server": {
    "host": "localhost",
    "port": 8080
  },
  "workflows": {
    "storage": "local",
    "path": "./workflows"
  },
  "agents": {
    "github_specialist": {
      "tools": ["github_api"],
      "model": "gemini-2.5-pro"
    },
    "ci_analyst": {
      "tools": ["ci_tools"],
      "model": "gemini-2.5-pro"
    },
    "code_reviewer": {
      "tools": ["code_analysis"],
      "model": "gemini-2.5-pro"
    },
    "security_scanner": {
      "tools": ["security_scan"],
      "model": "gemini-2.5-pro"
    },
    "comment_creator": {
      "tools": ["github_comments"],
      "model": "gemini-2.5-pro"
    }
  }
}
```

## Step 3: Start MCP Server

```bash
# Start Task Master MCP server
task-master serve --config task-master-config.json

# Or with Docker
docker run -p 8080:8080 -v $(pwd)/workflows:/app/workflows taskmaster/mcp-server
```

## Step 4: Test MCP Connection

```python
import httpx

async def test_mcp_connection():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8080/health")
        print(f"MCP Server Status: {response.status_code}")
        
        # Test workflow creation
        workflow_data = {
            "name": "test_workflow",
            "tasks": [
                {"id": "task1", "name": "Test Task"}
            ]
        }
        
        response = await client.post(
            "http://localhost:8080/workflows",
            json=workflow_data
        )
        print(f"Workflow Creation: {response.status_code}")
        print(f"Response: {response.json()}")

# Run test
asyncio.run(test_mcp_connection())
```

## Step 5: Environment Variables

```bash
export TASK_MASTER_MCP_URL="http://localhost:8080"
export TASK_MASTER_API_KEY="your-api-key"
export GITHUB_ACCESS_TOKEN="your-github-token"
```

## Step 6: Run Real Test

```bash
cd /Users/bhavraj/Documents/jupyter-ai-personas/jupyter_ai_personas/task_master
python test_mcp_real.py
```