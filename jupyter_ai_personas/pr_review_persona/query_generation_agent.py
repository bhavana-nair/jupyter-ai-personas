from agno.agent import Agent
from agno.models.aws import AwsBedrock
from .repo_analysis_tools import RepoAnalysisTools

class QueryGenerationAgent:
    def __init__(self, model_id, session):
        self.agent = Agent(
            name="query_generator",
            role="KG Query Specialist",
            model=AwsBedrock(id=model_id, session=session),
            instructions=[
                "You are a Neo4j Cypher query generation specialist for code analysis.",
                
                "SCHEMA KNOWLEDGE:",
                "- Nodes: Class, Function, File",
                "- Relationships: INHERITS_FROM, CONTAINS, CALLS",
                "- Properties: name, file, code, parameters, line_start, line_end",
                
                "QUERY GENERATION RULES:",
                "1. ANALYZE the change type and generate appropriate queries",
                "2. For CLASS changes: Focus on inheritance and method overrides",
                "3. For FUNCTION changes: Focus on callers and dependencies", 
                "4. For NEW files: Focus on similar patterns and naming conflicts",
                "5. ALWAYS use CONTAINS for partial matching",
                "6. GENERATE multiple queries for comprehensive analysis",
                
                "CHANGE TYPE PATTERNS:",
                "- Parent class modified → Find children + method overrides",
                "- Utility function changed → Find all callers + impact scope",
                "- Interface modified → Find implementations + consumers",
                "- New file added → Find similar patterns + conflicts",
                
                "OUTPUT FORMAT:",
                "Return a JSON array of queries with descriptions:",
                "[{\"query\": \"MATCH...\", \"purpose\": \"Find child classes\"}]"
            ],
            tools=[RepoAnalysisTools()],
            markdown=False
        )
    
    def generate_queries(self, change_description: str, file_names: list, change_type: str):
        """Generate KG queries for specific PR changes"""
        prompt = f"""
        Generate Neo4j Cypher queries for this PR change:
        
        Change Type: {change_type}
        Files Modified: {file_names}
        Description: {change_description}
        
        Generate comprehensive queries to analyze the impact of these changes.
        """
        
        response = self.agent.run(prompt)
        return response.content