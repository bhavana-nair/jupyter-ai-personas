import os
from typing import List
from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.github import GithubTools
from agno.tools.reasoning import ReasoningTools
from agno.tools.python import PythonTools
try:
    from .task_orchestrator import TaskOrchestrator, Task, TaskStatus
    from ..pr_review_persona.fetch_ci_failures import fetch_ci_failures
    from ..pr_review_persona.pr_comment_tool import create_inline_pr_comments
except ImportError:
    # For direct execution
    from task_orchestrator import TaskOrchestrator, Task, TaskStatus
    import sys
    sys.path.append('../pr_review_persona')
    from fetch_ci_failures import fetch_ci_failures
    from pr_comment_tool import create_inline_pr_comments

class PRTaskMaster:
    def __init__(self):
        self.orchestrator = TaskOrchestrator()
        self.github_token = os.getenv("GITHUB_ACCESS_TOKEN")
        
        if not self.github_token:
            raise ValueError("GITHUB_ACCESS_TOKEN required")
        
        os.environ['GITHUB_ACCESS_TOKEN'] = self.github_token
        self._setup_agents()
        self._setup_tasks()
    
    def _create_agent(self, name: str, role: str, instructions: List[str], tools: List) -> Agent:
        return Agent(
            name=name,
            role=role,
            model=Gemini(id="gemini-2.5-pro", api_key="AIzaSyCkD-2rU7O2Ubsf_iXV9rOZ2fmatZ5IxSA"),
            instructions=instructions,
            tools=tools,
            markdown=True
        )
    
    def _setup_agents(self):
        self.pr_fetcher = self._create_agent(
            "pr_fetcher", "PR Data Collector",
            [
                "Extract repository name and PR number from the input URL",
                "MUST call get_pull_requests and get_pull_request_changes tools",
                "Return the PR details and file changes found"
            ],
            [GithubTools(get_pull_requests=True, get_pull_request_changes=True)]
        )
        
        self.ci_analyzer = self._create_agent(
            "ci_analyzer", "CI/CD Analyst", 
            [
                "Extract repo name and PR number from input",
                "MUST call fetch_ci_failures tool with repo_name and pr_number",
                "Report CI status and any failures found"
            ],
            [fetch_ci_failures, ReasoningTools()]
        )
        
        self.code_reviewer = self._create_agent(
            "code_reviewer", "Code Quality Expert",
            [
                "Analyze the code changes provided in the context",
                "Look for code quality issues, patterns, and improvements",
                "Provide specific feedback on the code"
            ],
            [PythonTools(), ReasoningTools()]
        )
        
        self.security_scanner = self._create_agent(
            "security_scanner", "Security Specialist",
            [
                "Analyze the code changes for security issues",
                "Look for exposed secrets, vulnerabilities, and security risks",
                "Report any security concerns found"
            ],
            [PythonTools(), ReasoningTools()]
        )
        
        self.comment_creator = self._create_agent(
            "comment_creator", "PR Commenter",
            [
                "MUST call create_inline_pr_comments with comments on PR #4 changed files ONLY.",
                "PR #4 changed these files:",
                "- jupyter_ai_personas/pr_review_persona/fetch_ci_failures.py",
                "- jupyter_ai_personas/pr_review_persona/persona.py", 
                "- jupyter_ai_personas/pr_review_persona/pr_comment_tool.py",
                "- tests/test_pr_comment_tool.py",
                "ONLY comment on these exact file paths with position 1-3.",
                "Example: create_inline_pr_comments('bhavana-nair/jupyter-ai-personas', 4, [",
                "  {'path': 'jupyter_ai_personas/pr_review_persona/persona.py', 'position': 1, 'body': 'Nice work!'}",
                "])"
            ],
            [create_inline_pr_comments]
        )
    
    def _setup_tasks(self):
        # Task 1: Fetch PR data
        self.orchestrator.add_task(Task(
            id="fetch_pr",
            name="Fetch PR Data",
            agent=self.pr_fetcher,
            priority=10
        ))
        
        # Task 2: Analyze CI (depends on PR data)
        self.orchestrator.add_task(Task(
            id="analyze_ci", 
            name="Analyze CI Status",
            agent=self.ci_analyzer,
            dependencies=["fetch_pr"],
            priority=9
        ))
        
        # Task 3: Review code quality (parallel with CI)
        self.orchestrator.add_task(Task(
            id="review_code",
            name="Code Quality Review", 
            agent=self.code_reviewer,
            dependencies=["fetch_pr"],
            priority=8
        ))
        
        # Task 4: Security scan (parallel)
        self.orchestrator.add_task(Task(
            id="scan_security",
            name="Security Analysis",
            agent=self.security_scanner, 
            dependencies=["fetch_pr"],
            priority=7
        ))
        
        # Task 5: Create comments (depends on all analysis)
        self.orchestrator.add_task(Task(
            id="create_comments",
            name="Generate PR Comments",
            agent=self.comment_creator,
            dependencies=["analyze_ci", "review_code", "scan_security"],
            priority=5
        ))
    
    async def review_pr(self, pr_input: str) -> dict:
        # Set initial context
        self.orchestrator.shared_context['input'] = pr_input
        
        # Execute all tasks
        results = await self.orchestrator.execute_all()
        
        # Return consolidated results
        return {
            'status': self.orchestrator.get_task_status(),
            'results': results,
            'summary': self._generate_summary(results)
        }
    
    def _generate_summary(self, results: dict) -> str:
        summary_parts = []
        
        if 'fetch_pr' in results and results['fetch_pr']:
            summary_parts.append("✅ PR data fetched")
        
        if 'analyze_ci' in results:
            summary_parts.append("🔍 CI analysis completed")
        
        if 'review_code' in results:
            summary_parts.append("📝 Code review completed")
        
        if 'scan_security' in results:
            summary_parts.append("🔒 Security scan completed")
        
        if 'create_comments' in results:
            summary_parts.append("💬 Comments posted")
        
        return " | ".join(summary_parts)