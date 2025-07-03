import os
import subprocess
import tempfile
import re
from agno.tools import Toolkit
from agno.utils.log import logger
from agno.agent import Agent
import sys
sys.path.append('../knowledge_graph')
from jupyter_ai_personas.knowledge_graph.code_analysis_tool import CodeAnalysisTool
from jupyter_ai_personas.knowledge_graph.schema_validator import SchemaValidator

class RepoAnalysisTools(Toolkit):
    def __init__(self, **kwargs):
        self.code_tool = CodeAnalysisTool()
        self.schema_validator = SchemaValidator("neo4j://127.0.0.1:7687", ("neo4j", "Bhavana@97"))
        
        super().__init__(name="repo_analysis", tools=[
            self.get_schema_info,
            self.query_codebase,
            self.get_function_source,
            self.find_class_relationships,
            self.find_impact_analysis,
            self.debug_database_contents
        ], **kwargs)


    
    def get_schema_info(self, agent: Agent) -> str:
        """
        Get the knowledge graph schema information.
        
        Returns:
            str: Schema information for query writing
        """
        try:
            return self.schema_validator.generate_schema_info()
        except Exception as e:
            return f"Error getting schema: {str(e)}"
            


    def query_codebase(self, agent: Agent, query: str) -> str:
        """
        Execute a custom query on the analyzed codebase knowledge graph.
        
        Args:
            agent (Agent): The agent instance
            query (str): Cypher query to execute on the knowledge graph
            
        Returns:
            str: Query results
        """
        import time
        start_time = time.time()
        
        try:
            print(f"\n=== KG QUERY DEBUG ===")
            print(f"Full Cypher Query:")
            print(f"{query}")
            print(f"--- Executing Query ---")
            
            result = self.code_tool.query_code(query)
            query_time = time.time() - start_time
            
            print(f"Query Time: {query_time:.3f}s")
            print(f"Result Preview: {str(result)[:200]}...")
            print(f"=== END KG QUERY DEBUG ===\n")
            
            return result
        except Exception as e:
            print(f"KG Query Error: {str(e)}")
            print(f"=== END KG QUERY DEBUG ===\n")
            return f"Error executing query: {str(e)}"

    def get_function_source(self, agent: Agent, function_name: str, class_name: str = None) -> str:
        """
        Get the source code of a specific function from the analyzed repository.
        
        Args:
            agent (Agent): The agent instance
            function_name (str): Name of the function to retrieve
            class_name (str, optional): Name of the class containing the function
            
        Returns:
            str: Source code of the function
        """
        import time
        start_time = time.time()
        
        try:
            result = self.code_tool.get_function_code(function_name, class_name)
            query_time = time.time() - start_time
            print(f"KG Function Lookup - Function: '{function_name}' | Class: '{class_name}' | Time: {query_time:.3f}s")
            return result
        except Exception as e:
            return f"Error retrieving function source: {str(e)}"

    def find_class_relationships(self, agent: Agent, class_name: str) -> str:
        """
        Find inheritance relationships for a given class.
        
        Args:
            agent (Agent): The agent instance
            class_name (str): Name of the class to analyze
            
        Returns:
            str: Information about class relationships and structure
        """
        import time
        start_time = time.time()
        
        try:
            class_info = self.code_tool.get_class_info(class_name)
            related_classes = self.code_tool.find_related_classes(class_name)
            query_time = time.time() - start_time
            print(f"KG Class Analysis - Class: '{class_name}' | Time: {query_time:.3f}s")
            return f"{class_info}\n\n{related_classes}"
        except Exception as e:
            return f"Error analyzing class relationships: {str(e)}"
    
    def find_impact_analysis(self, agent: Agent, target_name: str, target_type: str = "Function") -> str:
        """
        Find all modules/functions that would break if target is removed.
        
        Args:
            agent (Agent): The agent instance
            target_name (str): Name of function/class to analyze
            target_type (str): "Function" or "Class"
            
        Returns:
            str: Impact analysis results
        """
        import time
        start_time = time.time()
        
        try:
            if target_type == "Function":
                query = f"""
                MATCH (dependent:Function)-[:CALLS*]->(target:Function {{name: '{target_name}'}})
                RETURN DISTINCT dependent.file as affected_file, dependent.name as affected_function
                ORDER BY affected_file
                """
            else:  # Class
                query = f"""
                MATCH (child:Class)-[:INHERITS_FROM*]->(target:Class {{name: '{target_name}'}})
                OPTIONAL MATCH (child)-[:CONTAINS]->(f:Function)
                RETURN DISTINCT child.file as affected_file, child.name as affected_class, f.name as affected_function
                ORDER BY affected_file
                """
            
            result = self.code_tool.query_code(query)
            query_time = time.time() - start_time
            print(f"KG Impact Analysis - Target: '{target_name}' | Type: '{target_type}' | Time: {query_time:.3f}s")
            return f"Impact Analysis for {target_type} '{target_name}':\n{result}"
        except Exception as e:
            return f"Error in impact analysis: {str(e)}"
    
    def debug_database_contents(self, agent: Agent) -> str:
        """
        Debug what's actually in the database.
        
        Returns:
            str: Database contents summary
        """
        try:
            # Check all node types and their properties
            query = """
            MATCH (n)
            RETURN labels(n) as node_labels, 
                   CASE WHEN n.file IS NOT NULL THEN n.file ELSE n.path END as file_path,
                   CASE WHEN n.name IS NOT NULL THEN n.name ELSE 'no_name' END as name,
                   CASE WHEN n.type IS NOT NULL THEN n.type ELSE 'no_type' END as type
            LIMIT 20
            """
            
            result = self.code_tool.query_code(query)
            return f"Database Contents Debug:\n{result}"
        except Exception as e:
            return f"Error debugging database: {str(e)}"