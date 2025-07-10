import os
import re
import tempfile
import subprocess
from jupyter_ai.personas.base_persona import BasePersona, PersonaDefaults
from jupyterlab_chat.models import Message
from jupyter_ai.history import YChatHistory
from agno.agent import Agent
from agno.models.aws import AwsBedrock
import boto3
from agno.tools.github import GithubTools
from agno.tools.reasoning import ReasoningTools
from agno.tools.file import FileTools
from agno.tools.shell import ShellTools
from langchain_core.messages import HumanMessage
from agno.tools.python import PythonTools
from agno.team.team import Team
from .template import PRCreationPersonaVariables, PR_CREATION_PROMPT_TEMPLATE
import sys
sys.path.append('../knowledge_graph')
from jupyter_ai_personas.knowledge_graph.bulk_analyzer import BulkCodeAnalyzer
from jupyter_ai_personas.pr_review_persona.repo_analysis_tools import RepoAnalysisTools

session = boto3.Session()

class PRCreationPersona(BasePersona):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.shared_analyzer = None

    @property
    def defaults(self):
        return PersonaDefaults(
            name="PRCreationPersona",
            avatar_path="/api/ai/static/jupyternaut.svg",
            description="A specialized assistant for analyzing issues and implementing code fixes with automated git operations.",
            system_prompt="You are a PR creation assistant that analyzes issues, designs solutions, and implements fixes with proper git workflow.",
        )

    def initialize_team(self, system_prompt):
        model_id = self.config.lm_provider_params["model_id"]
        github_token = os.getenv("GITHUB_ACCESS_TOKEN")
        if not github_token:
            raise ValueError("GITHUB_ACCESS_TOKEN environment variable is not set. Please set it with a plain GitHub personal access token.")

        # Issue Analysis Agent
        issue_analyzer = Agent(
            name="issue_analyzer",
            role="Issue Analysis Specialist",
            model=AwsBedrock(id=model_id, session=session),
            markdown=True,
            instructions=[
                "MANDATORY ISSUE ANALYSIS WORKFLOW - Follow these steps:",
                
                "STEP 1 - Parse Issue Requirements:",
                "   - Extract issue description and requirements",
                "   - Identify problem statement and expected behavior",
                "   - Determine scope and complexity",
                "   - List acceptance criteria",
                
                "STEP 2 - Repository Context Analysis:",
                "   - Use KG queries to understand codebase structure",
                "   - Identify relevant files and components",
                "   - Find similar patterns or existing implementations",
                "   - Analyze dependencies and relationships",
                
                "STEP 3 - Impact Assessment:",
                "   - Determine which files need modification",
                "   - Identify potential breaking changes",
                "   - Consider testing requirements",
                "   - Plan integration points",
                
                "OUTPUT: Structured analysis with clear requirements and affected components"
            ],
            tools=[RepoAnalysisTools(), ReasoningTools(add_instructions=True, think=True, analyze=True)]
        )

        # Architecture Designer Agent
        architect = Agent(
            name="architect",
            role="Solution Architecture Designer",
            model=AwsBedrock(id=model_id, session=session),
            markdown=True,
            instructions=[
                "MANDATORY ARCHITECTURE DESIGN WORKFLOW:",
                
                "STEP 1 - Solution Design:",
                "   - Design minimal solution architecture",
                "   - Plan file structure and organization",
                "   - Define interfaces and contracts",
                "   - Consider existing patterns and conventions",
                
                "STEP 2 - Implementation Strategy:",
                "   - Break down into implementable components",
                "   - Define clear separation of concerns",
                "   - Plan error handling and edge cases",
                "   - Consider performance implications",
                
                "STEP 3 - Integration Planning:",
                "   - Plan how new code integrates with existing",
                "   - Identify required imports and dependencies",
                "   - Consider backward compatibility",
                "   - Plan testing approach",
                
                "OUTPUT: Detailed implementation plan with file-by-file changes"
            ],
            tools=[RepoAnalysisTools(), ReasoningTools(add_instructions=True, think=True, analyze=True)]
        )

        # Code Implementation Agent
        code_implementer = Agent(
            name="code_implementer",
            role="Code Implementation Specialist",
            model=AwsBedrock(id=model_id, session=session),
            markdown=True,
            instructions=[
                "MANDATORY CODE IMPLEMENTATION WORKFLOW:",
                
                "STEP 1 - Repository Setup:",
                "   - Clone repository using shell commands",
                "   - Create feature branch with descriptive name",
                "   - Verify current codebase state",
                
                "STEP 2 - Code Implementation:",
                "   - Write MINIMAL code that addresses the issue",
                "   - Follow existing code patterns and style",
                "   - Implement proper error handling",
                "   - Focus ONLY on the specific issue requirements",
                
                "STEP 3 - File Operations:",
                "   - Create/modify files using FileTools",
                "   - Ensure proper file organization",
                "   - Maintain code consistency",
                
                "CRITICAL REQUIREMENTS:",
                "- Write ONLY the minimal code needed",
                "- Follow existing patterns exactly",
                "- NO verbose implementations",
                "- Focus on the specific issue only"
            ],
            tools=[
                ShellTools(),
                FileTools(),
                PythonTools(),
                RepoAnalysisTools(),
                ReasoningTools(add_instructions=True, think=True, analyze=True)
            ]
        )

        # Git Operations Agent
        git_manager = Agent(
            name="git_manager",
            role="Git Operations Manager",
            model=AwsBedrock(id=model_id, session=session),
            markdown=True,
            instructions=[
                "MANDATORY GIT WORKFLOW:",
                
                "STEP 1 - Repository Operations:",
                "   - Use shell commands for git operations",
                "   - Clone main branch from repository",
                "   - Verify repository state and structure",
                
                "STEP 2 - Branch Management:",
                "   - Create feature branch: git checkout -b feature/issue-description",
                "   - Use descriptive branch names based on issue",
                "   - Ensure branch is created from latest main",
                
                "STEP 3 - Commit Operations:",
                "   - Stage files: git add .",
                "   - Create clear commit messages: git commit -m 'description'",
                "   - Follow conventional commit format if used in repo",
                
                "STEP 4 - Push Operations:",
                "   - Push feature branch: git push -u origin branch-name",
                "   - DO NOT create pull request (user will do manually)",
                
                "CRITICAL REQUIREMENTS:",
                "- NEVER create pull requests automatically",
                "- Always push to feature branch, never main",
                "- Use clear, descriptive commit messages"
            ],
            tools=[
                ShellTools(),
                GithubTools(get_pull_requests=True, get_pull_request_changes=True),
                ReasoningTools(add_instructions=True, think=True, analyze=True)
            ]
        )

        # Create the coordinating team
        pr_creation_team = Team(
            name="pr-creation-team",
            mode="coordinate",
            members=[issue_analyzer, architect, code_implementer, git_manager],
            model=AwsBedrock(id=model_id, session=session),
            instructions=[
                "Coordinate PR creation process with clear separation of tasks:",
                
                "PHASE 1 - ANALYSIS (Issue Analyzer):",
                "   - Parse and understand the issue requirements",
                "   - Analyze repository context using KG queries",
                "   - Identify affected components and scope",
                "   - Provide structured analysis to team",
                
                "PHASE 2 - ARCHITECTURE (Architect):",
                "   - Wait for issue analysis completion",
                "   - Design minimal solution architecture",
                "   - Plan implementation strategy",
                "   - Create detailed file-by-file implementation plan",
                
                "PHASE 3 - IMPLEMENTATION (Code Implementer):",
                "   - Wait for architecture design completion",
                "   - Set up repository and create branch",
                "   - Implement code changes following the plan",
                "   - Write ONLY minimal code addressing the issue",
                "   - Ensure code follows existing patterns",
                
                "PHASE 4 - GIT OPERATIONS (Git Manager):",
                "   - Wait for code implementation completion",
                "   - Commit changes with clear messages",
                "   - Push feature branch to remote",
                "   - Provide branch information for manual PR creation",
                
                "COORDINATION RULES:",
                "- Each phase must complete before next begins",
                "- Share context and findings between agents",
                "- Maintain focus on minimal, targeted solutions",
                "- Ensure proper git workflow throughout",
                
                "Chat history: " + system_prompt
            ],
            markdown=True,
            show_members_responses=True,
            enable_agentic_context=True,
            add_datetime_to_instructions=True,
            tools=[
                ShellTools(),
                FileTools(),
                GithubTools(get_pull_requests=True, get_pull_request_changes=True),
                RepoAnalysisTools(),
                ReasoningTools(add_instructions=True, think=True, analyze=True)
            ]
        )

        return pr_creation_team

    async def process_message(self, message: Message):
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

        variables = PRCreationPersonaVariables(
            input=message.body,
            model_id=model_id,
            provider_name=provider_name,
            persona_name=self.name,
            context=history_text
        )
        
        system_prompt = PR_CREATION_PROMPT_TEMPLATE.format_messages(**variables.model_dump())[0].content
        
        try:
            # Auto-analyze repository if URL is provided
            self._auto_analyze_repo(message.body)
            
            team = self.initialize_team(system_prompt)
            response = team.run(
                message.body, 
                stream=False,
                stream_intermediate_steps=True,
                show_full_reasoning=True
            )

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
            error_message = f"PR Creation Error ({type(e).__name__}): {str(e)}\nAn unexpected error occurred while the PR creation team was processing your request."
            async def error_iterator():
                yield error_message
            await self.stream_message(error_iterator())
    
    def _auto_analyze_repo(self, issue_text: str):
        """Automatically extract repo URL and create knowledge graph"""
        patterns = [
            r'https://github\.com/([^/\s]+/[^/\s]+)',
            r'github\.com/([^/\s]+/[^/\s]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, issue_text)
            if match:
                repo_path = match.group(1).rstrip('/')
                repo_url = f"https://github.com/{repo_path}.git"
                return self._clone_and_analyze(repo_url)
        return None
    
    def _clone_and_analyze(self, repo_url: str):
        """Clone repository and create knowledge graph"""
        import time
        start_time = time.time()
        
        try:
            temp_dir = tempfile.mkdtemp()
            target_folder = os.path.join(temp_dir, "repo_analysis")
            
            clone_start = time.time()
            subprocess.run(["git", "clone", repo_url, target_folder], check=True, capture_output=True)
            clone_time = time.time() - clone_start
            
            kg_start = time.time()
            analyzer = BulkCodeAnalyzer("neo4j://127.0.0.1:7687", ("neo4j", "Bhavana@97"))
            analyzer.analyze_folder(target_folder, clear_existing=True)
            kg_time = time.time() - kg_start
            
            total_time = time.time() - start_time
            print(f"KG Creation Times - Clone: {clone_time:.2f}s, Analysis: {kg_time:.2f}s, Total: {total_time:.2f}s")
            
            return target_folder
            
        except Exception as e:
            print(f"Error analyzing repository {repo_url}: {e}")
            return None