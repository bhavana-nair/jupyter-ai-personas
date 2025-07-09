import os
from typing import List
from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.github import GithubTools
from agno.tools.reasoning import ReasoningTools
from agno.tools.python import PythonTools

try:
    from .hybrid_orchestrator import HybridOrchestrator, Task, TaskStatus
    from ..pr_review_persona.fetch_ci_failures import fetch_ci_failures
    from ..pr_review_persona.pr_comment_tool import create_inline_pr_comments
except ImportError:
    from hybrid_orchestrator import HybridOrchestrator, Task, TaskStatus
    import sys
    sys.path.append('../pr_review_persona')
    from fetch_ci_failures import fetch_ci_failures
    from pr_comment_tool import create_inline_pr_comments

class HybridPRMaster:
    def __init__(self):
        self.model = Gemini(id="gemini-2.5-pro", api_key="AIzaSyCkD-2rU7O2Ubsf_iXV9rOZ2fmatZ5IxSA")
        self.orchestrator = HybridOrchestrator(self.model)
        
        github_token = os.getenv("GITHUB_ACCESS_TOKEN")
        if not github_token:
            raise ValueError("GITHUB_ACCESS_TOKEN required")
        os.environ['GITHUB_ACCESS_TOKEN'] = github_token
        
        self._setup_agents()
        self._setup_workflow()
    
    def _create_agent(self, name: str, role: str, instructions: List[str], tools: List) -> Agent:
        return Agent(
            name=name,
            role=role,
            model=self.model,
            instructions=instructions,
            tools=tools,
            markdown=True
        )
    
    def _setup_agents(self):
        self.pr_fetcher = self._create_agent(
            "pr_fetcher", "PR Data Collector",
            ["Extract repo and PR info", "Fetch PR details and changes"],
            [GithubTools(get_pull_requests=True, get_pull_request_changes=True)]
        )
        
        self.ci_analyzer = self._create_agent(
            "ci_analyzer", "CI/CD Analyst", 
            ["Analyze CI failures", "Report CI status"],
            [fetch_ci_failures, ReasoningTools()]
        )
        
        self.code_reviewer = self._create_agent(
            "code_reviewer", "Code Quality Expert",
            ["Review code patterns", "Check complexity and style"],
            [PythonTools(), ReasoningTools()]
        )
        
        self.security_scanner = self._create_agent(
            "security_scanner", "Security Specialist",
            ["Scan for vulnerabilities", "Check for exposed secrets"],
            [PythonTools(), ReasoningTools()]
        )
        
        self.comment_creator = self._create_agent(
            "comment_creator", "PR Commenter",
            [
                "You are a friendly code reviewer. Create multiple inline PR comments.",
                "STEP 1: Extract repo_name and pr_number from input URL",
                "STEP 2: Analyze the previous task results for specific issues",
                "STEP 3: Create 3-5 inline comments on different files/lines",
                "STEP 4: Call create_inline_pr_comments with all comments",
                
                "Comment Guidelines:",
                "- Be conversational and helpful: 'Nice work here! One suggestion...'",
                "- Focus on specific code improvements",
                "- Comment on different aspects: code quality, security, documentation",
                "- Use line numbers that are likely in the diff (5-20)",
                
                "Example call:",
                "create_inline_pr_comments('owner/repo', 6, [",
                "  {'path': 'file1.py', 'position': 10, 'body': 'Great approach! Consider adding error handling here.'},",
                "  {'path': 'file2.py', 'position': 15, 'body': 'This looks good, but have you considered performance implications?'},",
                "  {'path': 'file3.py', 'position': 8, 'body': 'Nice clean code! Quick suggestion for readability...'}",
                "])",
                
                "MUST create multiple comments, not just one."
            ],
            [create_inline_pr_comments]
        )
    
    def _setup_workflow(self):
        """Define workflow with intelligent skip conditions"""
        
        # Always fetch PR data
        self.orchestrator.add_task(Task(
            id="fetch_pr",
            name="Fetch PR Data",
            agent=self.pr_fetcher,
            dependencies=[],
            priority=10
        ))
        
        # Skip CI analysis if already passing
        self.orchestrator.add_task(Task(
            id="analyze_ci", 
            name="Analyze CI Status",
            agent=self.ci_analyzer,
            dependencies=["fetch_pr"],
            priority=9,
            skip_condition="Skip if CI is already passing and no failures to analyze"
        ))
        
        # Skip code review for documentation-only changes
        self.orchestrator.add_task(Task(
            id="review_code",
            name="Code Quality Review", 
            agent=self.code_reviewer,
            dependencies=["fetch_pr"],
            priority=8,
            skip_condition="Skip if PR contains only documentation changes (*.md, *.txt files)"
        ))
        
        # Skip security scan for small PRs or doc-only changes
        self.orchestrator.add_task(Task(
            id="scan_security",
            name="Security Analysis",
            agent=self.security_scanner, 
            dependencies=["fetch_pr"],
            priority=7,
            skip_condition="Skip if PR is small (<50 lines) or contains only documentation changes"
        ))
        
        # Always create comments if we have analysis results
        self.orchestrator.add_task(Task(
            id="create_comments",
            name="Generate PR Comments",
            agent=self.comment_creator,
            dependencies=["analyze_ci", "review_code", "scan_security"],
            priority=5
        ))
    
    async def review_pr(self, pr_input: str) -> dict:
        """Execute intelligent PR review workflow"""
        results = await self.orchestrator.execute_workflow(pr_input)
        
        return {
            'status': results['status'],
            'results': results['results'],
            'summary': self._generate_summary(results['results'])
        }
    
    def _generate_summary(self, results: dict) -> str:
        summary_parts = []
        
        for task_id, result in results.items():
            if result and not result.startswith("Skipped"):
                if task_id == "fetch_pr":
                    summary_parts.append("✅ PR data fetched")
                elif task_id == "analyze_ci":
                    summary_parts.append("🔍 CI analysis completed")
                elif task_id == "review_code":
                    summary_parts.append("📝 Code review completed")
                elif task_id == "scan_security":
                    summary_parts.append("🔒 Security scan completed")
                elif task_id == "create_comments":
                    summary_parts.append("💬 Comments posted")
            elif result and result.startswith("Skipped"):
                summary_parts.append(f"⏭️ {task_id} skipped")
        
        return " | ".join(summary_parts)