import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document

class LangChainRAGAnalyzer:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vectorstore = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\nclass ", "\ndef ", "\n\n", "\n"]
        )
        
    def analyze_folder(self, folder_path):
        """Analyze all .py files and create vector store"""
        documents = []
        
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    documents.extend(self._process_file(file_path))
        
        if documents:
            chunks = self.text_splitter.split_documents(documents)
            self.vectorstore = FAISS.from_documents(chunks, self.embeddings)
            print(f"Created vector store with {len(chunks)} chunks")
    
    def _process_file(self, file_path):
        """Process a single Python file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return [Document(
                page_content=content,
                metadata={"file": file_path, "type": "python_file"}
            )]
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return []
    
    def search(self, query, k=5):
        """Search for relevant code chunks"""
        if not self.vectorstore:
            return []
        
        docs = self.vectorstore.similarity_search(query, k=k)
        return [{"content": doc.page_content, "metadata": doc.metadata} for doc in docs]
    
    def get_function_code(self, function_name):
        """Search for specific function"""
        query = f"def {function_name}"
        results = self.search(query, k=3)
        
        for result in results:
            if f"def {function_name}" in result["content"]:
                return result["content"]
        
        return f"Function {function_name} not found"