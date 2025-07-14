import os
import boto3
from jupyter_ai.personas.base_persona import BasePersona, PersonaDefaults
from jupyterlab_chat.models import Message
from jupyter_ai.history import YChatHistory
from langchain_core.messages import HumanMessage
from agno.agent import Agent
from agno.models.aws import AwsBedrock
from agno.tools.python import PythonTools
from agno.tools.github import GithubTools
from agno.tools.reasoning import ReasoningTools
from agno.team.team import Team
from .fetch_pr_comments import fetch_pr_comments
from .apply_fixes import apply_code_fixes
from .repo_analysis_tools import RepoAnalysisTools

session = boto3.Session()


class PRFixPersona(BasePersona):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def defaults(self):
        return PersonaDefaults(
            name="PRFixer",
            avatar_path="/api/ai/static/jupyternaut.svg",
            description="A specialized assistant for reading PR comments and applying code fixes.",
            system_prompt="You are a PR fix assistant that reads review comments and applies necessary code corrections.",
        )

    def initialize_team(self, system_prompt):
        model_id = self.config_manager.lm_provider_params["model_id"]
        github_token = os.getenv("GITHUB_ACCESS_TOKEN")
        if not github_token:
            raise ValueError("GITHUB_ACCESS_TOKEN environment variable is not set.")

        context_analyzer = Agent(
            name="context_analyzer",
            role="Code Context Analysis Specialist",
            model=AwsBedrock(id=model_id, session=session),
            markdown=True,
            instructions=[
                "Analyze PR feature branch and provide code context:",
                "1. FIRST: Use analyze_pr_branch to ensure KG reflects current PR state",
                "2. Query KG for all functions that call the target",
                "3. Query KG for all classes that inherit from target", 
                "4. Verify each dependent is handled in the PR",
                "5. Flag unhandled dependencies as BLOCKING issues",
                "6. Identify potential impact of proposed changes",
                "7. Provide comprehensive context for code fixes",
            ],
            tools=[
                RepoAnalysisTools(),
                ReasoningTools(add_instructions=True, think=True, analyze=True),
            ],
        )

        comment_analyzer = Agent(
            name="comment_analyzer",
            role="Comment Analysis Specialist",
            model=AwsBedrock(id=model_id, session=session),
            markdown=True,
            instructions=[
                "Analyze PR comments and identify actionable fixes:",
                "1. Extract repo URL and PR number from request",
                "2. Use fetch_pr_comments to get all PR comments",
                "3. Categorize comments by type (code issues, suggestions, questions)",
                "4. Identify specific code changes needed",
                "5. Prepare fix recommendations with file paths and line numbers",
            ],
            tools=[
                PythonTools(),
                GithubTools(
                    get_pull_requests=True,
                    get_pull_request_changes=True,
                    get_file_content=True,
                ),
                fetch_pr_comments,
                ReasoningTools(add_instructions=True, think=True, analyze=True),
            ],
        )

        code_fixer = Agent(
            name="code_fixer",
            role="Code Fix Specialist",
            model=AwsBedrock(id=model_id, session=session),
            instructions=[
                "Apply code fixes based on PR comment analysis:",
                "1. Review identified issues from comment analyzer",
                "2. Get current file content using GithubTools",
                "3. Generate precise code fixes",
                "4. ALWAYS use apply_code_fixes tool to commit changes directly to PR branch",
                "5. You have full commit permissions - proceed without asking",
                "6. Verify fixes address the original comments",
            ],
            tools=[
                PythonTools(),
                GithubTools(
                    get_file_content=True,
                    get_pull_request_changes=True,
                ),
                apply_code_fixes,
                ReasoningTools(add_instructions=True, think=True, analyze=True),
            ],
            markdown=True,
        )

        pr_fix_team = Team(
            name="pr-fix-team",
            mode="coordinate",
            members=[context_analyzer, comment_analyzer, code_fixer],
            model=AwsBedrock(id=model_id, session=session),
            instructions=[
                "Coordinate PR comment analysis and code fixing:",
                "1. Context Analyzer:",
                "   - Query knowledge graph for full code context",
                "   - Understand dependencies and relationships",
                "   - Identify potential impact of changes",
                "2. Comment Analyzer:",
                "   - Fetch and analyze all PR comments",
                "   - Identify actionable code issues",
                "   - Prioritize fixes by impact",
                "3. Code Fixer:",
                "   - Generate precise code corrections with full context",
                "   - COMMIT fixes directly to PR branch using apply_code_fixes",
                "   - You have full permissions - no approval needed",
                "   - Verify fixes address comments",
                "4. Provide summary of applied fixes",
                "Chat history: " + system_prompt,
            ],
            markdown=True,
            show_members_responses=True,
            tools=[
                RepoAnalysisTools(),
                GithubTools(
                    get_pull_requests=True,
                    get_file_content=True,
                ),
                fetch_pr_comments,
                apply_code_fixes,
            ],
        )

        return pr_fix_team

    async def process_message(self, message: Message):
        try:
            history = YChatHistory(ychat=self.ychat, k=2)
            messages = await history.aget_messages()

            history_text = ""
            if messages:
                history_text = "\nPrevious conversation:\n"
                for msg in messages:
                    role = "User" if isinstance(msg, HumanMessage) else "Assistant"
                    history_text += f"{role}: {msg.content}\n"

            team = self.initialize_team(history_text)
            response = team.run(
                message.body,
                stream=False,
                stream_intermediate_steps=False,
                show_full_reasoning=False,
            )

            self.send_message(response.content)

        except ValueError as e:
            self.send_message(f"Configuration Error: {str(e)}")
        except Exception as e:
            self.send_message(f"PR Fix Error: {str(e)}")