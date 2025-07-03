from agno.tools import Toolkit
from agno.agent import Agent
from .ast_rag_analyzer import ASTRAGAnalyzer

class ASTRAGAnalysisTools(Toolkit):
    def __init__(self, shared_analyzer=None, **kwargs):
        self.analyzer = shared_analyzer or ASTRAGAnalyzer() #a single instance of ASTRAGAnalyzer that gets shared across all agents to avoid duplicating the vector store.
        
        super().__init__(name="ast_rag_analysis", tools=[
            self.search_code,
            self.search_classes,
            self.search_functions,
            self.get_function_source,
            self.get_class_source
        ], **kwargs)

    def search_code(self, agent: Agent, query: str, k: int = 5) -> str:
        """Search for relevant code elements using semantic similarity"""
        import time
        start_time = time.time()
        
        try:
            results = self.analyzer.search(query, k)
            search_time = time.time() - start_time
            print(f"AST RAG Search - Query: '{query}' | Time: {search_time:.3f}s | Results: {len(results)}")
            
            # Log context awareness
            print(f"CONTEXT AWARENESS CHECK:")
            print(f"  Agent Query: '{query}'")
            print(f"  Retrieved: {[r['metadata'].get('name') for r in results]}")
            print(f"  Context Relevance: {'HIGH' if len(results) > 0 else 'LOW'}")
            
            if not results:
                return "No relevant code found"
            
            output = f"Found {len(results)} relevant code elements:\n\n"
            for i, result in enumerate(results, 1):
                meta = result['metadata']
                output += f"{i}. {meta.get('type', 'unknown').title()}: {meta.get('name', 'unnamed')}\n"
                output += f"   File: {meta.get('file', 'Unknown')}\n"
                if meta.get('class'):
                    output += f"   Class: {meta.get('class')}\n"
                output += f"   Code:\n{result['content'][:300]}...\n\n"
            
            return output
        except Exception as e:
            return f"Error searching code: {str(e)}"

    def search_classes(self, agent: Agent, query: str, k: int = 5) -> str:
        """Search specifically for class definitions"""
        import time
        start_time = time.time()
        
        try:
            results = self.analyzer.search_by_type(query, "class", k)
            search_time = time.time() - start_time
            print(f"AST RAG Class Search - Query: '{query}' | Time: {search_time:.3f}s | Results: {len(results)}")
            
            if not results:
                return "No relevant classes found"
            
            output = f"Found {len(results)} relevant classes:\n\n"
            for i, result in enumerate(results, 1):
                meta = result['metadata']
                output += f"{i}. Class: {meta.get('name', 'unnamed')}\n"
                output += f"   File: {meta.get('file', 'Unknown')}\n"
                output += f"   Lines: {meta.get('line_start', 0)}-{meta.get('line_end', 0)}\n"
                output += f"   Code:\n{result['content'][:400]}...\n\n"
            
            return output
        except Exception as e:
            return f"Error searching classes: {str(e)}"

    def search_functions(self, agent: Agent, query: str, k: int = 5) -> str:
        """Search specifically for function definitions"""
        import time
        start_time = time.time()
        
        try:
            results = self.analyzer.search_by_type(query, "function", k)
            search_time = time.time() - start_time
            print(f"AST RAG Function Search - Query: '{query}' | Time: {search_time:.3f}s | Results: {len(results)}")
            
            if not results:
                return "No relevant functions found"
            
            output = f"Found {len(results)} relevant functions:\n\n"
            for i, result in enumerate(results, 1):
                meta = result['metadata']
                output += f"{i}. Function: {meta.get('name', 'unnamed')}\n"
                output += f"   File: {meta.get('file', 'Unknown')}\n"
                if meta.get('class'):
                    output += f"   Class: {meta.get('class')}\n"
                if meta.get('parameters'):
                    output += f"   Parameters: {', '.join(meta.get('parameters', []))}\n"
                output += f"   Code:\n{result['content'][:400]}...\n\n"
            
            return output
        except Exception as e:
            return f"Error searching functions: {str(e)}"

    def get_function_source(self, agent: Agent, function_name: str, class_name: str = None) -> str:
        """Get specific function source code"""
        import time
        start_time = time.time()
        
        try:
            result = self.analyzer.get_function_code(function_name, class_name)
            search_time = time.time() - start_time
            print(f"AST RAG Function Lookup - Function: '{function_name}' | Time: {search_time:.3f}s")
            return result
        except Exception as e:
            return f"Error retrieving function: {str(e)}"

    def get_class_source(self, agent: Agent, class_name: str) -> str:
        """Get specific class source code"""
        import time
        start_time = time.time()
        
        try:
            result = self.analyzer.get_class_code(class_name)
            search_time = time.time() - start_time
            print(f"AST RAG Class Lookup - Class: '{class_name}' | Time: {search_time:.3f}s")
            return result
        except Exception as e:
            return f"Error retrieving class: {str(e)}"