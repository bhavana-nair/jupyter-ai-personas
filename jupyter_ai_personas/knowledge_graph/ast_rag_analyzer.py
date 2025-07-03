import os
import tree_sitter_python as tspython
from tree_sitter import Language, Parser
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document
from langchain.retrievers import BM25Retriever, EnsembleRetriever

class ASTRAGAnalyzer:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vectorstore = None
        self.bm25_retriever = None
        self.ensemble_retriever = None
        self.PY_LANGUAGE = Language(tspython.language())
        self.parser = Parser(self.PY_LANGUAGE)
        
    def analyze_folder(self, folder_path):
        """Analyze all .py files and create vector store with separate class/function documents"""
        documents = []
        
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    documents.extend(self._process_file(file_path))
        
        if documents:
            self.vectorstore = FAISS.from_documents(documents, self.embeddings)
            self.bm25_retriever = BM25Retriever.from_documents(documents)
            self.ensemble_retriever = EnsembleRetriever(
                retrievers=[self.bm25_retriever, self.vectorstore.as_retriever()],
                weights=[0.4, 0.6]
            )
            
            print(f"Created hybrid retrieval system with {len(documents)} separate code elements")
    
    def _process_file(self, file_path):
        """Extract classes and functions as separate documents"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            tree = self.parser.parse(bytes(code, 'utf8'))
            documents = []
            self._extract_elements(tree.root_node, file_path, code, documents)
            return documents
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return []
    
    def _extract_elements(self, node, file_path, code, documents, current_class=None):
        """Recursively extract classes and functions as separate documents"""
        if node.type == 'class_definition':
            class_name = node.child_by_field_name("name").text.decode('utf8')
            class_code = node.text.decode('utf8', errors='ignore')
            
            documents.append(Document(
                page_content=class_code,
                metadata={
                    "file": file_path,
                    "type": "class",
                    "name": class_name,
                    "line_start": node.start_point[0],
                    "line_end": node.end_point[0]
                }
            ))
            
            for child in node.children:
                self._extract_elements(child, file_path, code, documents, class_name)
        
        elif node.type == 'function_definition':
            func_name = node.child_by_field_name("name").text.decode('utf8')
            func_code = node.text.decode('utf8', errors='ignore')
            
            params_node = node.child_by_field_name("parameters")
            params = []
            if params_node:
                for child in params_node.children:
                    if child.type == 'identifier':
                        params.append(child.text.decode('utf8'))
            
            documents.append(Document(
                page_content=func_code,
                metadata={
                    "file": file_path,
                    "type": "function",
                    "name": func_name,
                    "class": current_class,
                    "parameters": params,
                    "line_start": node.start_point[0],
                    "line_end": node.end_point[0]
                }
            ))
        
        else:
            for child in node.children:
                self._extract_elements(child, file_path, code, documents, current_class)
    
    def search(self, query, k=5):
        """Search for relevant code elements"""
        if not self.vectorstore:
            return []
        
        docs = self.ensemble_retriever.get_relevant_documents(query)[:k]

        print(f"\n=== RAG RETRIEVAL DEBUG ===")
        print(f"Query: '{query}'")
        print(f"Retrieved {len(docs)} chunks:")
        for i, doc in enumerate(docs, 1):
            meta = doc.metadata
            print(f"\n--- Chunk {i} ---")
            print(f"Type: {meta.get('type', 'unknown')}")
            print(f"Name: {meta.get('name', 'unnamed')}")
            print(f"File: {meta.get('file', 'unknown')}")
            if meta.get('class'):
                print(f"Class: {meta.get('class')}")
            print(f"Content (first 200 chars): {doc.page_content[:200]}...")
        print(f"=== END RETRIEVAL DEBUG ===\n")
        
        return [{"content": doc.page_content, "metadata": doc.metadata} for doc in docs]
    
    def search_by_type(self, query, element_type, k=5):
        """Search for specific type of code elements (class/function)"""
        if not self.vectorstore:
            return []
        
        docs = self.vectorstore.similarity_search(query, k=k*2)  
        filtered = [doc for doc in docs if doc.metadata.get("type") == element_type]
        
        # Log filtered retrieval
        print(f"\n=== RAG TYPE SEARCH DEBUG ===")
        print(f"Query: '{query}' | Type: '{element_type}'")
        print(f"Found {len(docs)} total, filtered to {len(filtered)} {element_type}s:")
        for i, doc in enumerate(filtered[:k], 1):
            meta = doc.metadata
            print(f"\n--- {element_type.title()} {i} ---")
            print(f"Name: {meta.get('name', 'unnamed')}")
            print(f"File: {meta.get('file', 'unknown')}")
            print(f"Content (first 150 chars): {doc.page_content[:150]}...")
        print(f"=== END TYPE SEARCH DEBUG ===\n")
        
        return [{"content": doc.page_content, "metadata": doc.metadata} for doc in filtered[:k]]
    
    
    def get_function_code(self, function_name, class_name=None):
        """Get specific function code"""
        if not self.vectorstore:
            return f"Function {function_name} not found"
        
        # Search with function name
        search_query = f"def {function_name}"
        docs = self.vectorstore.similarity_search(search_query, k=10)
        
        # Log function search
        print(f"\n=== FUNCTION LOOKUP DEBUG ===")
        print(f"Looking for function: '{function_name}' in class: '{class_name}'")
        print(f"Search query: '{search_query}'")
        print(f"Found {len(docs)} candidates:")
        
        for i, doc in enumerate(docs, 1):
            meta = doc.metadata
            is_match = (meta.get("type") == "function" and 
                       meta.get("name") == function_name and
                       (class_name is None or meta.get("class") == class_name))
            print(f"  {i}. {meta.get('name', 'unnamed')} | Type: {meta.get('type')} | Class: {meta.get('class')} | Match: {is_match}")
        
        for doc in docs:
            if (doc.metadata.get("type") == "function" and 
                doc.metadata.get("name") == function_name):
                if class_name is None or doc.metadata.get("class") == class_name:
                    print(f"✓ Found matching function!")
                    print(f"=== END FUNCTION LOOKUP DEBUG ===\n")
                    return doc.page_content
        
        print(f"✗ Function not found")
        print(f"=== END FUNCTION LOOKUP DEBUG ===\n")
        return f"Function {function_name} not found"
    
    def get_class_code(self, class_name):
        """Get specific class code"""
        if not self.vectorstore:
            return f"Class {class_name} not found"
        
        docs = self.vectorstore.similarity_search(f"class {class_name}", k=10)
        
        for doc in docs:
            if (doc.metadata.get("type") == "class" and 
                doc.metadata.get("name") == class_name):
                return doc.page_content
        
        return f"Class {class_name} not found"