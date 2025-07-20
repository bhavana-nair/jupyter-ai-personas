import os
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
from .ci_tools import CITools
from .template import PRPersonaVariables, PR_PROMPT_TEMPLATE

session = boto3.Session()

from typing import List, Dict, Optional, Any
from agno.models.base import BaseModel

class PRReviewPersona(BasePersona):
    """PR Review Persona for analyzing and providing feedback on GitHub pull requests.
    
    This persona coordinates a team of specialized agents to perform comprehensive
    code review, security analysis, and documentation checks on pull requests.
    """
    
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the PR Review Persona.
        
        Args:
            *args: Variable length argument list passed to BasePersona
            **kwargs: Arbitrary keyword arguments passed to BasePersona
        """
        super().__init__(*args, **kwargs)

    @property
    def defaults(self):
        return PersonaDefaults(
            name="PRReviewPersona",
            avatar_path="/api/ai/static/jupyternaut.svg",
            description="A specialized assistant for reviewing pull requests and providing detailed feedback.",
            system_prompt="You are a PR reviewer assistant that helps analyze code changes, provide feedback, and ensure code quality.",
        )
    

    def initialize_team(self, system_prompt: str) -> Team:
        """Initialize and configure the PR review team with specialized agents.
        
        Args:
            system_prompt (str): The system prompt containing chat history and context
            
        Returns:
            Team: Configured team of specialized agents for PR review
            
        Raises:
            ValueError: If GitHub token is not set or invalid
            RuntimeError: If team initialization fails
        """
        try:
            model_id = self.config.lm_provider_params["model_id"]
            github_token = self._validate_github_token()
            
            team_members = [
                self._create_code_quality_agent(model_id),
                self._create_documentation_agent(model_id),
                self._create_security_agent(model_id),
                self._create_github_agent(model_id)
            ]
            
            return self._create_review_team(model_id, team_members, system_prompt)
            
        except Exception as e:
            logger.error(f"Failed to initialize PR review team: {str(e)}")
            raise RuntimeError(f"Team initialization failed: {str(e)}")
            
    def _validate_github_token(self) -> str:
        """Validate the GitHub access token.
        
        Returns:
            str: Validated GitHub token
            
        Raises:
            ValueError: If token is not set or invalid
        """
        github_token = os.getenv("GITHUB_ACCESS_TOKEN")
        if not github_token:
            raise ValueError(
                "GITHUB_ACCESS_TOKEN environment variable is not set. "
                "Please set it with a plain GitHub personal access token."
            )
        return github_token
        model_id = self.config.lm_provider_params["model_id"]
        github_token = os.getenv("GITHUB_ACCESS_TOKEN")
        if not github_token:
            raise ValueError("GITHUB_ACCESS_TOKEN environment variable is not set. Please set it with a plain GitHub personal access token (not GitHub Actions syntax).")

    def _create_code_quality_agent(self, model_id: str) -> Agent:
        """Create the code quality analysis agent.
        
        Args:
            model_id (str): The AWS Bedrock model ID to use
            
        Returns:
            Agent: Configured code quality analysis agent
        """
        return Agent(
            name="code_quality",
            role="Code Quality Analyst",
            model=AwsBedrock(
                id=model_id,
                session=session
            ),
            markdown=True,
            instructions=[
                "You have access to CITools for analyzing CI failures. Always:",
                
                "1. Get repository and PR information:",
                "   - Extract repo URL and PR number from the request",
                "   - Use GithubTools to fetch PR details",
                
                "2. Check CI failures using CITools:",
                "   - Call fetch_ci_failure_data with repo_url and pr_number",
                "   - Use get_ci_logs to analyze any failures found",
                "   - If failures exist, analyze error messages and logs",
                
                "3. Review code quality:",
                "   - Code style and consistency",
                "   - Code smells and anti-patterns",
                "   - Complexity and readability",
                "   - Performance implications",
                "   - Error handling and edge cases",
                
                "Always include CI analysis in your response, whether failures are found or not.",
            ],
            tools=[
                PythonTools(),
                # PRTools(),
                GithubTools( get_pull_requests= True, get_pull_request_changes= True, create_pull_request_comment= True ),
                CITools(),
                ReasoningTools(add_instructions=True, think=True, analyze=True)
            ]
        )

    def _create_documentation_agent(self, model_id: str) -> Agent:
        """Create the documentation review agent.
        
        Args:
            model_id (str): The AWS Bedrock model ID to use
            
        Returns:
            Agent: Configured documentation review agent
        """
        return Agent(
            name="documentation_checker",
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

    def _create_security_agent(self, model_id: str) -> Agent:
        """Create the security analysis agent.
        
        Args:
            model_id (str): The AWS Bedrock model ID to use
            
        Returns:
            Agent: Configured security analysis agent
        """
        return Agent(
            name="security_checker",
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
            tools=[PythonTools(), ReasoningTools(add_instructions=True, think=True, analyze=True,)],
            markdown=True
        )

    def _create_github_agent(self, model_id: str) -> Agent:
        """Create the GitHub operations agent.
        
        Args:
            model_id (str): The AWS Bedrock model ID to use
            
        Returns:
            Agent: Configured GitHub operations agent
        """
        return Agent(
            name="github",
            role="GitHub Specialist",
            model=AwsBedrock(
                id=model_id,
                session=session
            ),
            instructions=[
                "Monitor and analyze GitHub repository activities and changes",
                "Fetch and process pull request data",
                "Analyze code changes and provide structured feedback",
                "Create a comment on a specific line of a specific file in a pull request.",
                "Note: Requires a valid GitHub personal access token in GITHUB_ACCESS_TOKEN environment variable"
            ],
            tools=[
                GithubTools( create_pull_request_comment= True, get_pull_requests= True, get_pull_request_changes= True),
                # PRTools()
            ],
            markdown=True
        )


    def _create_review_team(self, model_id: str, members: List[Agent], system_prompt: str) -> Team:
        """Create the PR review team with the specified members.
        
        Args:
            model_id (str): The AWS Bedrock model ID to use
            members (List[Agent]): List of specialized agents for the team
            system_prompt (str): System prompt containing context and history
            
        Returns:
            Team: Configured PR review team
        """
        return Team(
            name="pr-review-team",
            mode="coordinate",
            members=members,
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
                "   - Manage repository operations",
                "   - Keep PR metadata minimal",
                
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
                GithubTools( create_pull_request_comment= True, get_pull_requests= True, get_pull_request_changes= True),
                ReasoningTools(add_instructions=True, think=True, analyze=True)
            ]
        )

        return pr_review_team

    async def process_message(self, message: Message) -> None:
        """Process an incoming message and generate a PR review response.
        
        Args:
            message (Message): The incoming chat message to process
            
        Raises:
            ValueError: If configuration or input is invalid
            boto3.exceptions.Boto3Error: If AWS API calls fail
            Exception: For other unexpected errors
        """
        provider_name = self.config.lm_provider.name
        model_id = self.config.lm_provider_params["model_id"]

        history = YChatHistory(ychat=self.ychat, k=2)
        messages = await history.aget_messages()
        
        history_text = ""
        if messages:
            history_text = "\nPrevious conversation:\n"
            for msg in messages:
                role = "User" if isinstance(msg, HumanMessage) else "Assistant"
                history_text += f"{role}: {msg.content}\n"

        variables = PRPersonaVariables(
            input=message.body,
            model_id=model_id,
            provider_name=provider_name,
            persona_name=self.name,
            context=history_text
        )
        
        system_prompt = PR_PROMPT_TEMPLATE.format_messages(**variables.model_dump())[0].content
        # team = self.initialize_team(system_prompt)
        
        try:
            team = self.initialize_team(system_prompt)
            response = team.run(message.body, 
                              stream=False,
                              stream_intermediate_steps=True,
                              show_full_reasoning=True)

            response = response.content
            async def response_iterator():
                yield response
            
            await self.stream_message(response_iterator())
            
        except ValueError as e:
            error_message = f"Configuration Error: {str(e)}\nThis may be due to missing or invalid environment variables, model configuration, or input parameters."
            async def error_iterator():
                yield error_message
            await self.stream_message(error_iterator())
            
        except boto3.exceptions.Boto3Error as e:
            error_message = f"AWS Connection Error: {str(e)}\nThis may be due to invalid AWS credentials or network connectivity issues."
            async def error_iterator():
                yield error_message
            await self.stream_message(error_iterator())
            
        except Exception as e:
            error_message = f"PR Review Error ({type(e).__name__}): {str(e)}\nAn unexpected error occurred while the PR review team was analyzing your request."
            async def error_iterator():
                yield error_message
            await self.stream_message(error_iterator())