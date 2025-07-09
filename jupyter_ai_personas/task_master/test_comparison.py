import asyncio
import sys
import os
import time

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pr_task_master import PRTaskMaster
from hybrid_pr_master import HybridPRMaster
from managed_team_master import ManagedTeamMaster

async def compare_approaches():
    """Compare different task orchestration approaches"""
    
    pr_input = "https://github.com/bhavana-nair/jupyter-ai-personas/pull/6"
    
    print("🔬 TASK ORCHESTRATION COMPARISON")
    print("=" * 60)
    
    approaches = [
        ("Custom Task Orchestrator", PRTaskMaster),
        ("Hybrid Orchestrator", HybridPRMaster), 
        ("Managed Team", ManagedTeamMaster)
    ]
    
    results = {}
    
    for name, approach_class in approaches:
        print(f"\n🧪 Testing: {name}")
        print("-" * 40)
        
        start_time = time.time()
        
        try:
            if name == "Managed Team":
                # ManagedTeamMaster returns string directly
                master = approach_class()
                result = await master.review_pr(pr_input)
                
                results[name] = {
                    "success": True,
                    "result": result[:200] + "..." if len(result) > 200 else result,
                    "duration": time.time() - start_time,
                    "type": "string"
                }
            else:
                # Other approaches return dict
                master = approach_class()
                result = await master.review_pr(pr_input)
                
                results[name] = {
                    "success": True,
                    "result": result.get('summary', 'No summary'),
                    "duration": time.time() - start_time,
                    "type": "dict",
                    "tasks_completed": len([s for s in result.get('status', {}).values() 
                                          if s.value == 'completed'])
                }
                
        except Exception as e:
            results[name] = {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time
            }
        
        # Show immediate result
        if results[name]["success"]:
            print(f"✅ Completed in {results[name]['duration']:.2f}s")
            if results[name]["type"] == "dict":
                print(f"📊 Tasks completed: {results[name]['tasks_completed']}")
            print(f"📝 Result: {results[name]['result']}")
        else:
            print(f"❌ Failed: {results[name]['error']}")
    
    # Final comparison
    print("\n" + "=" * 60)
    print("📊 FINAL COMPARISON")
    print("=" * 60)
    
    for name, result in results.items():
        if result["success"]:
            print(f"\n✅ {name}:")
            print(f"   Duration: {result['duration']:.2f}s")
            if result["type"] == "dict":
                print(f"   Tasks: {result['tasks_completed']}")
            print(f"   Output: {result['result']}")
        else:
            print(f"\n❌ {name}: {result['error']}")

if __name__ == "__main__":
    asyncio.run(compare_approaches())