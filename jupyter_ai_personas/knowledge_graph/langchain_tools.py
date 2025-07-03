from agno.tools import Toolkit
from agno.agent import Agent
from .langchain_rag_analyzer import LangChainRAGAnalyzer

class LangChainAnalysisTools(Toolkit):
    def __init__(self, shared_analyzer=None, **kwargs):
        self.analyzer = shared_analyzer or LangChainRAGAnalyzer()
        
        super().__init__(name="langchain_analysis", tools=[
            self.search_code,
            self.get_function_source
        ], **kwargs)

    def search_code(self, agent: Agent, query: str, k: int = 5) -> str:
        """Search for relevant code using LangChain vector search"""
        import time
        start_time = time.time()
        
        try:
            results = self.analyzer.search(query, k)
            search_time = time.time() - start_time
            print(f"RAG Search - Query: '{query}' | Time: {search_time:.3f}s | Results: {len(results)}")
            
            if not results:
                return "No relevant code found"
            
            output = f"Found {len(results)} relevant code chunks:\n\n"
            for i, result in enumerate(results, 1):
                output += f"{i}. File: {result['metadata'].get('file', 'Unknown')}\n"
                output += f"   Content:\n{result['content'][:400]}...\n\n"
            
            return output
        except Exception as e:
            return f"Error searching code: {str(e)}"

    def get_function_source(self, agent: Agent, function_name: str) -> str:
        """Get specific function source code"""
        import time
        start_time = time.time()
        
        try:
            result = self.analyzer.get_function_code(function_name)
            search_time = time.time() - start_time
            print(f"RAG Function Lookup - Function: '{function_name}' | Time: {search_time:.3f}s")
            return result
        except Exception as e:
            return f"Error retrieving function: {str(e)}"