import os
from typing import List
from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.github import GithubTools
from agno.tools.reasoning import ReasoningTools
from agno.tools.python import PythonTools
from agno.team.team import Team

try:
    from ..pr_review_persona.fetch_ci_failures import fetch_ci_failures
    from ..pr_review_persona.pr_comment_tool import create_inline_pr_comments
except ImportError:
    import sys
    sys.path.append('../pr_review_persona')
    from fetch_ci_failures import fetch_ci_failures
    from pr_comment_tool import create_inline_pr_comments

class ManagedTeamMaster:
    def __init__(self):
        self.model = Gemini(id="gemini-2.5-pro", api_key="AIzaSyCkD-2rU7O2Ubsf_iXV9rOZ2fmatZ5IxSA")
        
        github_token = os.getenv("GITHUB_ACCESS_TOKEN")
        if not github_token:
            raise ValueError("GITHUB_ACCESS_TOKEN required")
        os.environ['GITHUB_ACCESS_TOKEN'] = github_token
        
        self._setup_team()
    
    def _create_agent(self, name: str, role: str, instructions: List[str], tools: List) -> Agent:
        return Agent(
            name=name,
            role=role,
            model=self.model,
            instructions=instructions,
            tools=tools,
            markdown=True
        )
    
    def _setup_team(self):
        # Task Master Agent - Controls the workflow
        task_master = self._create_agent(
            "task_master", "Workflow Manager",
            [
                "You are the TASK MASTER - you control the PR review workflow.",
                "STRICT WORKFLOW ORDER:",
                "1. FIRST: Direct GitHub Specialist to fetch PR data",
                "2. WAIT for PR data confirmation before proceeding",
                "3. THEN: Direct CI Analyst to check CI status", 
                "4. PARALLEL: Direct Code Reviewer and Security Scanner to analyze",
                "5. FINALLY: Direct Comment Creator to make inline comments",
                "",
                "CONTROL RULES:",
                "- Only ONE agent works at a time (except parallel steps)",
                "- Verify each agent completes their task before moving on",
                "- If an agent doesn't use their required tool, make them retry",
                "- Track progress: 'Task X completed, moving to Task Y'",
                "",
                "AGENT ASSIGNMENTS:",
                "- GitHub Specialist: Fetch PR data ONLY",
                "- CI Analyst: Check CI failures ONLY", 
                "- Code Reviewer: Analyze code quality ONLY",
                "- Security Scanner: Check vulnerabilities ONLY",
                "- Comment Creator: Create inline comments ONLY",
                "",
                "PREVENT DUPLICATES:",
                "- Stop agents from repeating completed tasks",
                "- If PR data already fetched, don't fetch again",
                "- Maintain task completion status"
            ],
            [ReasoningTools()]  # Only reasoning tools for coordination
        )
        
        # GitHub Specialist - Only fetches data
        github_specialist = self._create_agent(
            "github_specialist", "PR Data Fetcher",
            [
                "You ONLY fetch PR data. That's your single responsibility.",
                "WAIT for Task Master to assign you the PR URL",
                "MUST use GitHub tools to fetch PR details and changes",
                "Report back: 'PR data fetched successfully' when done",
                "DO NOT analyze code or create comments - that's other agents' jobs"
            ],
            [GithubTools(get_pull_requests=True, get_pull_request_changes=True, 
                        get_file_content=True, get_directory_content=True)]
        )
        
        # CI Analyst - Only checks CI
        ci_analyst = self._create_agent(
            "ci_analyst", "CI Status Checker", 
            [
                "You ONLY check CI status. That's your single responsibility.",
                "WAIT for Task Master to assign you after PR data is ready",
                "MUST use fetch_ci_failures tool with repo name and PR number",
                "Report back: 'CI analysis completed' when done",
                "DO NOT fetch PR data or create comments"
            ],
            [fetch_ci_failures, ReasoningTools()]
        )
        
        # Code Reviewer - Only reviews code
        code_reviewer = self._create_agent(
            "code_reviewer", "Code Quality Analyst",
            [
                "You ONLY review code quality. That's your single responsibility.", 
                "WAIT for Task Master to assign you after PR data is ready",
                "Analyze code patterns, complexity, style, and best practices",
                "Report back: 'Code review completed' when done",
                "DO NOT fetch data or create comments"
            ],
            [PythonTools(), ReasoningTools()]
        )
        
        # Security Scanner - Only scans security
        security_scanner = self._create_agent(
            "security_scanner", "Security Analyst",
            [
                "You ONLY scan for security issues. That's your single responsibility.",
                "WAIT for Task Master to assign you after PR data is ready", 
                "Check for vulnerabilities, exposed secrets, and security risks",
                "Report back: 'Security scan completed' when done",
                "DO NOT fetch data or create comments"
            ],
            [PythonTools(), ReasoningTools()]
        )
        
        # Comment Creator - Only creates comments
        comment_creator = self._create_agent(
            "comment_creator", "PR Commenter",
            [
                "You ONLY create inline PR comments. That's your single responsibility.",
                "WAIT for Task Master to assign you after ALL analysis is complete",
                "MUST use create_inline_pr_comments tool to post multiple comments",
                "Create 3-5 friendly, helpful inline comments based on team analysis",
                "Report back: 'Comments created successfully' when done"
            ],
            [create_inline_pr_comments]
        )
        
        # Create the managed team
        self.team = Team(
            name="managed-pr-review-team",
            mode="coordinate",
            members=[task_master, github_specialist, ci_analyst, code_reviewer, security_scanner, comment_creator],
            model=self.model,
            instructions=[
                "This is a MANAGED TEAM with a dedicated Task Master.",
                "",
                "WORKFLOW CONTROL:",
                "- Task Master controls all workflow decisions",
                "- Other agents ONLY act when directed by Task Master",
                "- Each agent has ONE specific responsibility",
                "- No agent should work outside their assigned role",
                "",
                "EXECUTION ORDER:",
                "1. Task Master starts and directs GitHub Specialist",
                "2. GitHub Specialist fetches PR data",
                "3. Task Master directs CI Analyst", 
                "4. Task Master directs Code Reviewer and Security Scanner in parallel",
                "5. Task Master directs Comment Creator with all analysis results",
                "",
                "COMMUNICATION PROTOCOL:",
                "- Task Master: 'GitHub Specialist, please fetch PR data for: [URL]'",
                "- Agent: 'Task completed successfully' or 'Task failed: [reason]'",
                "- Task Master: 'Moving to next task...'",
                "",
                "QUALITY CONTROL:",
                "- Task Master verifies each agent used their required tools",
                "- If tools not used, Task Master requests retry",
                "- No duplicate work allowed"
            ],
            markdown=True,
            show_members_responses=True
        )
    
    async def review_pr(self, pr_input: str) -> str:
        """Execute managed PR review workflow"""
        try:
            response = await self.team.arun(
                f"Task Master: Please coordinate a complete PR review for: {pr_input}"
            )
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            return f"Managed team review failed: {str(e)}"