#!/usr/bin/env python3
"""Simple test to verify Claude API access."""

import os
import requests
import json

def test_claude_api():
    """Test access to Claude API using environment variable."""
    api_key = os.getenv('ANTHROPIC_API_KEY')
    
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        return False
    
    print(f"Using API key: {api_key[:8]}...{api_key[-4:]}")
    
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    url = "https://api.anthropic.com/v1/messages"
    
    data = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 100,
        "messages": [
            {"role": "user", "content": "Hello, Claude! This is a simple test."}
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        
        print("\nAPI Response:")
        print(f"Status code: {response.status_code}")
        print(f"Response content: {json.dumps(result, indent=2)}")
        
        if "content" in result and len(result["content"]) > 0:
            print("\nClaude's response:")
            print(result["content"][0]["text"])
            return True
        else:
            print("Error: Unexpected response format")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"\nAPI Request Error: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Status code: {e.response.status_code}")
            print(f"Response content: {e.response.text}")
        return False

if __name__ == "__main__":
    success = test_claude_api()
    print(f"\nTest {'succeeded' if success else 'failed'}")