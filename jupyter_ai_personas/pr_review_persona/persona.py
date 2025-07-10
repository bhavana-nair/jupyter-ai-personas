import os
import subprocess
import tempfile
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
from .ci_tools import CITools
# from jupyter_ai_personas.knowledge_graph.ast_rag_tools import ASTRAGAnalysisTools
from .repo_analysis_tools import RepoAnalysisTools
from .template import PRPersonaVariables, PR_PROMPT_TEMPLATE
import sys
sys.path.append('../knowledge_graph')
from jupyter_ai_personas.knowledge_graph.bulk_analyzer import BulkCodeAnalyzer

session = boto3.Session()

class PRReviewPersona(BasePersona):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.shared_analyzer = None

    @property
    def defaults(self):
        return PersonaDefaults(
            name="PRReviewPersona",
            avatar_path="/api/ai/static/jupyternaut.svg",
            description="A specialized assistant for reviewing pull requests and providing detailed feedback.",
            system_prompt="You are a PR reviewer assistant that helps analyze code changes, provide feedback, and ensure code quality.",
        )
    

    def initialize_team(self, system_prompt):
        model_id = self.config.lm_provider_params["model_id"]
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
                "MANDATORY PR REVIEW WORKFLOW - You MUST follow these steps in order:",
                
                "STEP 1 - Get PR Information (MANDATORY - NO EXCEPTIONS):",
                "   - Extract repo URL and PR number from the request",
                "   - IMMEDIATELY call get_pull_request_changes(repo_url, pr_number)",
                "   - NEVER proceed without actual PR diff data",
                "   - NEVER make assumptions about PR content",
                "   - NEVER fabricate or guess what the PR contains",
                "   - Parse the ACTUAL diff to identify modified functions and classes",
                "   - Use GithubTools to fetch PR details",
                "   - SHOW the actual PR diff in your response as evidence",
                
                "STEP 2 - MANDATORY KG Analysis for EVERY changed file:",
                
                "   - For EACH file in PR diff, you MUST run these KG queries:",
                "     a) query_codebase: MATCH (n) WHERE n.file CONTAINS 'filename' RETURN n.name, n.type",
                "     b) For each modified function: get_function_source(function_name)",
                "     c) For each modified class: find_class_relationships(class_name)",
                "   - For NEW files: MUST search for similar patterns with CONTAINS queries",
                "   - For MODIFIED files: MUST get current implementation before reviewing changes",
                "   - NEVER skip KG analysis - even if file seems simple",
                "   - ONLY use properties: 'name', 'file', 'code', 'parameters'",
                
                "STEP 3 - Query Generation & Context Analysis (REQUIRED):",
                
                "   - FIRST: Describe the changes to the Query Generation Agent",
                "   - REQUEST: FOCUSED KG queries limited to PR scope",
                "   - EXECUTE: Only targeted queries, avoid system-wide searches",
                "   - CHECK DEPENDENCIES: Use check_dependents_handled for each modified function/class",
                "   - ANALYZE: Results within the context of actual changes",
                "   - The Query Agent will provide specialized Cypher queries based on:",
                "     * Change type (class/function/interface/utility)",
                "     * Risk level (high-impact vs isolated changes)",
                "     * Relationship patterns (inheritance/calls/dependencies)",
                
                "STEP 4 - CI Analysis (REQUIRED):",
                "   - Call fetch_ci_failure_data with repo_url and pr_number",
                "   - Use get_ci_logs to analyze any failures found",
                
                "STEP 5 - Final Review (REQUIRED):",
                "   - Synthesize KG insights with PR changes",
                "   - HIGHLIGHT unhandled dependencies as critical issues",
                "   - Code style and consistency",
                "   - Code smells and anti-patterns",
                "   - Performance implications",
                
                "CRITICAL REQUIREMENTS:",
                "- NEVER review without actual PR data",
                "- NEVER make up PR content or changes",
                "- ALWAYS show actual diff data as evidence",
                "- FAILURE TO FETCH REAL PR DATA = INVALID REVIEW",
                "- You MUST show evidence of KG queries for each changed file",
            ],
            tools=[
                PythonTools(),
                GithubTools( get_pull_requests= True, get_pull_request_changes= True, create_pull_request_comment= True ),
                CITools(),
                # ASTRAGAnalysisTools(shared_analyzer=self.shared_analyzer),
                RepoAnalysisTools(),
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
            tools=[PythonTools(), ReasoningTools(add_instructions=True, think=True, analyze=True,)],
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
                "Repository analyzed with knowledge graph for code relationships",
                "Provide code context using graph-based analysis",
                "Create a comment on a specific line of a specific file in a pull request.",
                "Note: Requires a valid GitHub personal access token in GITHUB_ACCESS_TOKEN environment variable"
            ],
            tools=[
                GithubTools( create_pull_request_comment= True, get_pull_requests= True, get_pull_request_changes= True),
                # ASTRAGAnalysisTools(shared_analyzer=self.shared_analyzer)
                RepoAnalysisTools()
            ],
            markdown=True
        )

        # Create Query Generation Agent
        query_generator = Agent(name="query_generator",
            role="KG Query Specialist",
            model=AwsBedrock(
                id=model_id,
                session=session
            ),
            instructions=[
                "You are a Neo4j Cypher query generation specialist for code analysis.",
                
                "SCHEMA KNOWLEDGE:",
                "- Nodes: Class, Function, File",
                "- Relationships: INHERITS_FROM, CONTAINS, CALLS",
                "- Properties: name, file, code, parameters, line_start, line_end",
                
                "QUERY GENERATION RULES - STAY FOCUSED:",
                "1. ONLY query for DIRECT dependencies of changed code",
                "2. LIMIT scope to 1-2 levels of relationships maximum",
                "3. For CLASS changes: Only immediate children, not entire hierarchy",
                "4. For FUNCTION changes: Only direct callers, not call chains",
                "5. For NEW files: Only check naming conflicts in same module",
                "6. AVOID deep traversals like [:CALLS*] or [:INHERITS_FROM*]",
                "7. CONSTRAIN queries with file path filters when possible",
                
                "FOCUSED CHANGE PATTERNS:",
                "- Parent class modified → Find DIRECT children only",
                "- Function changed → Find DIRECT callers in same module",
                "- New file added → Check conflicts in same directory",
                "- Method signature changed → Check overrides in direct subclasses",
                
                "SCOPE LIMITATIONS:",
                "- NO system-wide searches",
                "- NO deep relationship traversals",
                "- PREFER file-path constraints",
                "- LIMIT results to 10-20 items maximum",
                
                "EXAMPLE FOCUSED QUERIES:",
                "- MATCH (child:Class)-[:INHERITS_FROM]->(parent:Class {name: 'PRPersona'}) RETURN child.name LIMIT 5",
                "- MATCH (f:Function)-[:CALLS]->(target:Function {name: 'process_message'}) WHERE f.file CONTAINS 'persona' RETURN f.name LIMIT 10",
                "- MATCH (n) WHERE n.file CONTAINS 'pr_review' AND n.name CONTAINS 'new_function' RETURN n.name",
                
                "OUTPUT FORMAT:",
                "Return a JSON array of FOCUSED queries:",
                "[{\"query\": \"MATCH...\", \"purpose\": \"Find direct children\", \"scope\": \"limited\"}]"
            ],
            tools=[RepoAnalysisTools()],
            markdown=False
        )
        
        pr_review_team = Team(
            name="pr-review-team",
            mode="coordinate",
            members=[query_generator, code_quality, documentation_checker, security_checker, gitHub],
            model=AwsBedrock(
                id=model_id,
                session=session
            ),
            instructions=[
                "Coordinate PR review process with specialized team members:",
                
                "1. Query Generator:",
                "   - WAIT for GitHub Specialist to provide ACTUAL PR diff data",
                "   - Generate queries ONLY based on real changes from diff",
                "   - NEVER generate queries based on assumptions",
                "   - Provide query recommendations to other team members",
                
                "2. Code Quality Analyst:",
                "   - MUST execute KG queries for EVERY file in PR diff",
                "   - MUST show query results in response as evidence",
                "   - MUST analyze relationships and dependencies",
                "   - Check CI status and analyze any failures",
                "   - Provide comprehensive analysis with codebase context",
                
                "3. Documentation Specialist:",
                "   - Review documentation completeness",
                "   - Focus on critical documentation issues",
                
                "4. Security Analyst:",
                "   - Check for security vulnerabilities",
                "   - Prioritize high-impact issues",
                
                "5. GitHub Specialist:",
                "   - FIRST ACTION: Call get_pull_request_changes() with actual repo URL and PR number",
                "   - VERIFY: Show actual PR diff data in response",
                "   - NEVER proceed without real GitHub data",
                "   - MUST run KG queries for each changed file from ACTUAL diff",
                "   - Provide deep code context using graph traversal and queries",
                "   - Keep PR metadata minimal",
                
                "6. Synthesize findings:",
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
                # ASTRAGAnalysisTools(shared_analyzer=self.shared_analyzer),
                RepoAnalysisTools(),
                ReasoningTools(add_instructions=True, think=True, analyze=True)
            ]
        )

        return pr_review_team

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

        variables = PRPersonaVariables(
            input=message.body,
            model_id=model_id,
            provider_name=provider_name,
            persona_name=self.name,
            context=history_text
        )
        
        system_prompt = PR_PROMPT_TEMPLATE.format_messages(**variables.model_dump())[0].content
        
        try:
            self._auto_analyze_repo(message.body)
            
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
    
    def _auto_analyze_repo(self, pr_text: str):
        """Automatically extract repo URL and create knowledge graph/ RAG """
        patterns = [
            r'https://github\.com/([^/\s]+/[^/\s]+)',
            r'github\.com/([^/\s]+/[^/\s]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, pr_text)
            if match:
                repo_path = match.group(1).rstrip('/')
                repo_url = f"https://github.com/{repo_path}.git"
                self._clone_and_analyze(repo_url)
                break
    
    def _clone_and_analyze(self, repo_url: str):
        """Clone repository and create RAG embeddings"""
        import time
        start_time = time.time()
        
        try:
            temp_dir = tempfile.mkdtemp()
            target_folder = os.path.join(temp_dir, "repo_analysis")
            
            clone_start = time.time()
            subprocess.run(["git", "clone", repo_url, target_folder], check=True, capture_output=True)
            clone_time = time.time() - clone_start
            
            # from jupyter_ai_personas.knowledge_graph.ast_rag_analyzer import ASTRAGAnalyzer
            # self.shared_analyzer = ASTRAGAnalyzer()
            
            kg_start = time.time()
            analyzer = BulkCodeAnalyzer("neo4j://127.0.0.1:7687", ("neo4j", "Bhavana@97"))
            analyzer.analyze_folder(target_folder, clear_existing=True)
            # self.shared_analyzer.analyze_folder(target_folder)
            kg_time = time.time() - kg_start
            
            total_time = time.time() - start_time
            print(f"KG Creation Times - Clone: {clone_time:.2f}s, Analysis: {kg_time:.2f}s, Total: {total_time:.2f}s")
            
        except Exception as e:
            print(f"Error analyzing repository {repo_url}: {e}")