import os
from jupyter_ai.personas.base_persona import BasePersona, PersonaDefaults
from jupyterlab_chat.models import Message
from jupyter_ai.history import YChatHistory
from agno.agent import Agent
import boto3
from agno.tools.github import GithubTools
from agno.tools.reasoning import ReasoningTools
from langchain_core.messages import HumanMessage
from agno.tools.python import PythonTools
from agno.team.team import Team
from .fetch_ci_failures import fetch_ci_failures
from agno.models.google import Gemini
from .template import PRPersonaVariables, PR_PROMPT_TEMPLATE
from .pr_comment_tool import create_inline_pr_comments

session = boto3.Session()

class PRReviewPersonaG(BasePersona):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def defaults(self):
        return PersonaDefaults(
            name="PRReviewPersona_gemini",
            avatar_path="/api/ai/static/jupyternaut.svg",
            description="A specialized assistant for reviewing pull requests and providing detailed feedback.",
            system_prompt="You are a PR reviewer assistant that helps analyze code changes, provide feedback, and ensure code quality.",
        )
    
    def initialize_team(self, system_prompt):
        # model_id = self.config.lm_provider_params["model_id"]
        github_token = os.getenv("GITHUB_ACCESS_TOKEN")
        
        if github_token:
            os.environ['GITHUB_ACCESS_TOKEN'] = github_token
        if not github_token:
            raise ValueError("GITHUB_ACCESS_TOKEN environment variable is not set. Please set it with a plain GitHub personal access token (not GitHub Actions syntax).")

        code_quality = Agent(name="code_quality",
            role="Code Quality Analyst",
            model=Gemini(
            id="gemini-2.5-pro",
            api_key="AIzaSyCkD-2rU7O2Ubsf_iXV9rOZ2fmatZ5IxSA"
        ),
            markdown=True,
            instructions=[
                "Review code quality and analyze CI failures:",
                
                "1. Get repository and PR information:",
                "   - Extract repo URL and PR number from the request",
                "   - Use GithubTools to fetch PR details",
                
                "2. ALWAYS check CI failures:",
                "   - MUST call fetch_ci_failures with repo_name and pr_number",
                "   - If failures found, analyze error messages and logs",
                "   - If no failures, mention that CI is passing",
                "   - Include CI status in your final report",
                
                "3. Review code quality:",
                "   - Code style and consistency",
                "   - Code smells and anti-patterns",
                "   - Complexity and readability",
                "   - Performance implications",
                "   - Error handling and edge cases",
                
                f"GitHub token is configured: {bool(github_token)}"
            ],
            tools=[
                PythonTools(),
                GithubTools(get_pull_requests=True, get_pull_request_changes=True, get_file_content = True, get_directory_content= True),
                fetch_ci_failures,
                ReasoningTools(add_instructions=True, think=True, analyze=True)
            ]
        )

        documentation_checker = Agent(name="documentation_checker",
            role="Documentation Specialist",
            model=Gemini(
            id="gemini-2.5-pro",
            api_key="AIzaSyCkD-2rU7O2Ubsf_iXV9rOZ2fmatZ5IxSA"
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
           model=Gemini(
            id="gemini-2.5-pro",
            api_key="AIzaSyCkD-2rU7O2Ubsf_iXV9rOZ2fmatZ5IxSA"
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

        gitHub = Agent(name="github",
            role="GitHub Specialist",
            model=Gemini(
            id="gemini-2.5-pro",
            api_key="AIzaSyCkD-2rU7O2Ubsf_iXV9rOZ2fmatZ5IxSA"
        ),
            instructions=[
                "Monitor and analyze GitHub repository activities and changes",
                "Fetch and process pull request data",
                "Analyze code changes and provide structured feedback",
                "ALWAYS create inline PR comments for specific issues found:",
                "   - Use create_inline_pr_comments to post comments on specific lines",
                "   - Include repo_name, pr_number, and list of comments with path/position/body",
                "   - Comment on code issues, suggestions, and improvements",
                "Note: Requires a valid GitHub personal access token in GITHUB_ACCESS_TOKEN environment variable"
            ],
            tools=[
                GithubTools(create_pull_request_comment=True, get_pull_requests=True, get_pull_request_changes=True),
                ReasoningTools(add_instructions=True, think=True, analyze=True),
                create_inline_pr_comments
            ],
            markdown=True
        )


        pr_review_team = Team(
            name="pr-review-team",
            mode="coordinate",
            members=[code_quality, documentation_checker, security_checker, gitHub],
            model=Gemini(
            id="gemini-2.5-pro",
            api_key="AIzaSyCkD-2rU7O2Ubsf_iXV9rOZ2fmatZ5IxSA"
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
                "   - Create inline PR comments for specific issues",
                "   - Use create_inline_pr_comments tool when issues are found",
                
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
                GithubTools(create_pull_request_comment=True, get_pull_requests=True, get_pull_request_changes=True),
                ReasoningTools(add_instructions=True, think=True, analyze=True),
                create_inline_pr_comments
            ]
        )

        return pr_review_team

    async def process_message(self, message: Message):
        # provider_name = self.config.lm_provider.name
        # model_id = self.config.lm_provider_params["model_id"]

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
            model_id="",
            provider_name= "",
            persona_name=self.name,
            context=history_text
        )
        
        system_prompt = PR_PROMPT_TEMPLATE.format_messages(**variables.model_dump())[0].content
        team = self.initialize_team(system_prompt)
        
        try:
            team = self.initialize_team(system_prompt)
            response = team.run(message.body, 
                              stream=False,
                              stream_intermediate_steps=False,
                              show_full_reasoning=False)

            self.send_message(response.content)
            
        except ValueError as e:
            error_message = f"Configuration Error: {str(e)}\nThis may be due to missing or invalid environment variables, model configuration, or input parameters."
            self.send_message(error_message)
            
        except Exception as e:
            error_message = f"PR Review Error ({type(e).__name__}): {str(e)}\nAn unexpected error occurred while the PR review team was analyzing your request."
            self.send_message(error_message)




        # try:
        #     team = self.initialize_team(system_prompt)
        #     response = team.run(message.body, 
        #                       stream=True,
        #                       stream_intermediate_steps=True,
        #                       show_full_reasoning=True)

        #     async def async_response():
        #         for chunk in response:
        #             if hasattr(chunk, 'content') and chunk.content:
        #                 yield chunk.content
        #             elif isinstance(chunk, str):
        #                 yield chunk


            # response = response.content
            # async def response_iterator():
            #     yield response

            # await self.stream_message(response_iterator())
        
        #     await self.stream_message(async_response())

        # except ValueError as e:
        #     error_message = f"Configuration Error: {str(e)}\nThis may be due to missing or invalid environment variables, model configuration, or input parameters."
        #     async def error_iterator():
        #         yield error_message
        #     await self.stream_message(error_iterator())

        # except boto3.exceptions.Boto3Error as e:
        #     error_message = f"AWS Connection Error: {str(e)}\nThis may be due to invalid AWS credentials or network connectivity issues."
        #     async def error_iterator():
        #         yield error_message
        #     await self.stream_message(error_iterator())

        # except Exception as e:
        #     error_message = f"PR Review Error ({type(e).__name__}): {str(e)}\nAn unexpected error occurred while the PR review team was analyzing your request."
        #     async def error_iterator():
        #         yield error_message
        #     await self.stream_message(error_iterator())