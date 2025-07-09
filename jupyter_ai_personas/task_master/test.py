import asyncio
import sys
import os

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from managed_team_master import ManagedTeamMaster

async def main():
    try:
        # Initialize the managed team master
        team_master = ManagedTeamMaster()
        
        pr_input = "https://github.com/bhavana-nair/jupyter-ai-personas/pull/6"
        
        print("Starting MANAGED TEAM PR review workflow...")
        print("Task Master agent will coordinate the entire workflow.")
        print("\n" + "="*60)
        
        result = await team_master.review_pr(pr_input)
        
        print("\n" + "="*50)
        print("MANAGED TEAM RESULTS")
        print("="*50)
        print(result)
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())