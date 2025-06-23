import os
import re
from jupyter_ai.personas.base_persona import BasePersona, PersonaDefaults
from jupyterlab_chat.models import Message
from jupyter_ai.history import YChatHistory
from agno.agent import Agent
from agno.models.aws import AwsBedrock
import boto3
from agno.tools.github import GithubTools
from agno.tools.reasoning import ReasoningTools
from langchain_core.messages import HumanMessage
from agno.tools.python import PythonTools
from agno.team.team import Team


session = boto3.Session()


def initialize_team(self, system_prompt):
        model_id = getattr(self.config.lm_provider_params, "model_id", "anthropic.claude-3-5-sonnet-20240422-v1:0")
        github_token = os.getenv("GITHUB_ACCESS_TOKEN")
        if not github_token:
            raise ValueError("GITHUB_ACCESS_TOKEN environment variable is not set. Please set it with a plain GitHub personal access token (not GitHub Actions syntax).")

        code_quality = Agent(name="code_quality",
            role="Code Quality Analyst",
            model=AwsBedrock(
                id=model_id,
                session=session
            ),
            markdown=True,
            instructions=[
                "1. Get repository and PR information:",
                "   - Extract repo URL and PR number from the request",
                "   - Use GithubTools to fetch PR details",
                
                "2. Review code quality:",
                "   - Code style and consistency",
                "   - Code smells and anti-patterns",
                "   - Complexity and readability",
                "   - Performance implications",
                "   - Error handling and edge cases",
            ],
            tools=[
                PythonTools(),
                GithubTools(get_pull_requests=True,
                           get_pull_request_changes=True, 
                           create_pull_request_comment=True,
                           get_repository=True,
                           get_pull_request_with_details=True,
                           create_review_request=True,
                           search_code=True),
                ReasoningTools(add_instructions=True, think=True, analyze=True)
            ]
        )

        documentation_checker = Agent(name="documentation_checker",
            role="Documentation Specialist",
            model=AwsBedrock(
                id=model_id,
                session=session
            ),
            instructions=[
                "Review documentation completeness and quality:",
                "1. Verify docstrings for new/modified functions and classes",
                "2. Check README updates for new features or changes",
                "3. Verify return value documentation",
                "4. Check for documentation consistency",
            ],
            tools=[PythonTools()],
            markdown=True
        )

        security_checker = Agent(name="security_checker",
            role="Security Analyst",
            model=AwsBedrock(
                id=model_id,
                session=session
            ),
            instructions=[
                "Perform security analysis of code changes:",
                "1. Check for exposed sensitive information (API keys, tokens, credentials)",
                "2. Identify potential SQL injection vulnerabilities",
                "3. Verify proper input sanitization",
                "4. Check for insecure direct object references",
            ],
            tools=[PythonTools(), ReasoningTools(add_instructions=True, think=True, analyze=True)],
            markdown=True
        )

        gitHub = Agent(name="github",
            role="GitHub Specialist",
            model=AwsBedrock(
                id=model_id,
                session=session
            ),
            instructions=[
                "Monitor and analyze GitHub repository activities and changes",
                "Fetch and process pull request data",
                "Analyze code changes and provide structured feedback",
                "Create inline comments on specific lines of files in a pull request",
                "Submit a general review message with the review",
                "Note: Requires a valid GitHub personal access token in GITHUB_ACCESS_TOKEN environment variable"
            ],
            tools=[
                GithubTools(create_pull_request_comment=True, 
                           get_pull_requests=True, 
                           get_pull_request_changes=True,
                           get_repository=True,
                           get_pull_request_with_details=True,
                           create_review_request=True,
                           create_review=True,
                           create_review_comment=True)
            ],
            markdown=True
        )


        pr_review_team = Team(
            name="pr-review-team",
            mode="coordinate",
            members=[code_quality, documentation_checker, security_checker, gitHub],
            model=AwsBedrock(
                id=model_id,
                session=session
            ),
            instructions=[
                "Coordinate PR review process with specialized team members:",
                
                "1. Code Quality Analyst:",
                "   - Review code structure and patterns",
                "   - Check CI status and analyze any failures",
                "   - Keep analysis focused and concise",
                
                "2. Documentation Specialist:",
                "   - Review documentation completeness",
                "   - Focus on critical documentation issues",
                
                "3. Security Analyst:",
                "   - Check for security vulnerabilities",
                "   - Prioritize high-impact issues",
                
                "4. GitHub Specialist:",
                "   - Create inline comments on specific lines of code",
                "   - Submit a general review message with the review",
                "   - Use create_review_comment for inline comments",
                "   - Use create_review for the general review message",
                
                "5. Synthesize findings:",
                "   - Combine key insights from all members",
                "   - Focus on actionable items",
                "   - Keep responses concise",
                
                "Chat history: " + system_prompt
            ],
            markdown=True,
            show_members_responses=True,
            enable_agentic_context=True,
            add_datetime_to_instructions=True,
            tools=[
                GithubTools(create_pull_request_comment=True, 
                           get_pull_requests=True, 
                           get_pull_request_changes=True,
                           create_review=True,
                           create_review_comment=True),
                ReasoningTools(add_instructions=True, think=True, analyze=True)
            ]
        )

        return pr_review_team
