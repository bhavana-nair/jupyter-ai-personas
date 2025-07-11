import os
import tree_sitter_python as tspython
from tree_sitter import Language, Parser
from neo4j import GraphDatabase
import hashlib
import logging

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create console handler with a higher log level
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create file handler which logs even debug messages
file_handler = logging.FileHandler('bulk_analyzer.log')
file_handler.setLevel(logging.DEBUG)

# Create formatters and add them to the handlers
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

console_formatter = logging.Formatter('%(levelname)s: %(message)s')
console_handler.setFormatter(console_formatter)

# Add the handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

class BulkCodeAnalyzer:
    def __init__(self, uri=None, auth=None):
        # Use environment variables with secure credential handling
        self.uri = uri or os.getenv('NEO4J_URI', 'neo4j://localhost:7687')
        neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
        neo4j_password = os.getenv('NEO4J_PASSWORD')
        self.auth = auth or (neo4j_user, neo4j_password)
        
        # Validate required credentials
        if not self.auth[1]:
            logger.error('NEO4J_PASSWORD environment variable not set')
            raise ValueError('Database password must be provided via NEO4J_PASSWORD environment variable')
        
        try:
            # Initialize database connection
            logger.info(f'Connecting to Neo4j database at {self.uri}')
            self.driver = GraphDatabase.driver(self.uri, auth=self.auth)
            
            # Test connection
            with self.driver.session() as session:
                session.run("MATCH () RETURN 1 LIMIT 1")
            logger.info('Successfully connected to Neo4j database')
            
            # Initialize parser
            self.PY_LANGUAGE = Language(tspython.language())
            self.parser = Parser(self.PY_LANGUAGE)
            logger.debug('Tree-sitter parser initialized')
            
        except Exception as e:
            logger.error(f'Failed to connect to Neo4j database: {str(e)}', exc_info=True)
            raise ConnectionError(f'Failed to connect to Neo4j database: {str(e)}')
    
    def analyze_folder(self, folder_path, clear_existing=False):
        """Analyze all supported files in a folder and add to knowledge graph"""
        if clear_existing:
            with self.driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")
                print("Cleared existing graph")
        
        # Supported file extensions
        supported_extensions = {'.py', '.ts', '.js', '.tsx', '.jsx'}
        
        all_files = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_ext = os.path.splitext(file)[1]
                if file_ext in supported_extensions:
                    all_files.append(os.path.join(root, file))
        
        print(f"Found {len(all_files)} supported files")
        
        with self.driver.session() as session:
            for file_path in all_files:
                print(f"Analyzing: {file_path}")
                try:
                    if file_path.endswith('.py'):
                        self._analyze_file(file_path, session)
                    else:
                        self._analyze_non_python_file(file_path, session)
                except Exception as e:
                    print(f"Error analyzing {file_path}: {e}")
    
    def _analyze_file(self, file_path, session):
        # Validate and normalize file path
        file_path = os.path.abspath(os.path.normpath(file_path))
        base_dir = os.path.abspath(os.getcwd())
        
        # Prevent directory traversal
        if not file_path.startswith(base_dir):
            raise ValueError('File path must be within current working directory')
            
        if not os.path.exists(file_path):
            raise FileNotFoundError(f'File not found: {file_path}')
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        tree = self.parser.parse(bytes(code, 'utf8'))
        self._extract_code_elements(tree.root_node, session, file_path)
    
    def _extract_code_elements(self, node, session, file_path, current_class=None):
        if node.type == 'class_definition':
            class_name = node.child_by_field_name("name").text.decode('utf8')
            session.run(
                "MERGE (c:Class {name: $name}) SET c.file = $file",
                name=class_name, file=file_path
            )
            
            superclasses = node.child_by_field_name("superclasses")
            if superclasses:
                for child in superclasses.children:
                    if child.type == 'identifier':
                        parent = child.text.decode('utf8')
                        session.run("MERGE (parent:Class {name: $parent})", parent=parent)
                        session.run(
                            "MATCH (parent:Class {name: $parent}), (child:Class {name: $child}) "
                            "MERGE (child)-[:INHERITS_FROM]->(parent)",
                            parent=parent, child=class_name
                        )
            
            for child in node.children:
                self._extract_code_elements(child, session, file_path, class_name)
        
        elif node.type == 'function_definition':
            func_name = node.child_by_field_name("name").text.decode('utf8')
            func_code = node.text.decode('utf8', errors='ignore')
            
            params_node = node.child_by_field_name("parameters")
            params = []
            if params_node:
                for child in params_node.children:
                    if child.type == 'identifier':
                        params.append(child.text.decode('utf8'))
            
            code_hash = hashlib.md5(func_code.encode()).hexdigest()
            
            session.run(
                "MERGE (f:Function {name: $name, file: $file}) "
                "SET f.code = $code, f.code_hash = $hash, f.parameters = $params, f.line_start = $start, f.line_end = $end",
                name=func_name, file=file_path, code=func_code, hash=code_hash, params=params,
                start=node.start_point[0], end=node.end_point[0]
            )
            
            if current_class:
                session.run(
                    "MATCH (c:Class {name: $class_name}), (f:Function {name: $func_name, file: $file}) "
                    "MERGE (c)-[:CONTAINS]->(f)",
                    class_name=current_class, func_name=func_name, file=file_path
                )
            
            # Extract function calls
            self._extract_function_calls(node, session, func_name, file_path)
        
        else:
            for child in node.children:
                self._extract_code_elements(child, session, file_path, current_class)
    
    def _analyze_non_python_file(self, file_path, session):
        """Analyze non-Python files (basic content indexing)"""
        logger.info(f'Analyzing non-Python file: {file_path}')

        try:
            # Validate and normalize file path
            file_path = os.path.abspath(os.path.normpath(file_path))
            base_dir = os.path.abspath(os.getcwd())
            
            # Security: Prevent directory traversal
            if not file_path.startswith(base_dir):
                logger.error(f'Path traversal attempt blocked: {file_path}')
                raise ValueError('File path must be within current working directory')
                
            if not os.path.exists(file_path):
                logger.error(f'File not found: {file_path}')
                raise FileNotFoundError(f'File not found: {file_path}')
            
            # Read and process file
            logger.debug(f'Reading file: {file_path}')
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                file_type = os.path.splitext(file_path)[1]
                logger.info(f'Processing {file_type} file of size {len(content)} bytes')
                
                # Create a File node with limited content size
                session.run(
                    "MERGE (f:File {path: $path}) SET f.content = $content, f.size = $size, f.type = $type",
                    path=file_path, 
                    content=content[:5000],  # Limit content size for storage efficiency
                    size=len(content),
                    type=file_type
                )
                logger.debug(f'Successfully created File node for {file_path}')
                
            except Exception as e:
                # Handle file processing errors
                logger.error(f'Error processing {file_path}: {str(e)}', exc_info=True)
                
                # Create File node with error state for traceability
                session.run(
                    "MERGE (f:File {path: $path}) SET f.error = $error, f.type = $type, f.status = 'error'",
                    path=file_path,
                    error=str(e),
                    type=os.path.splitext(file_path)[1]
                )
                logger.info(f'Created error state node for {file_path}')
                raise  # Re-raise for proper error propagation
                
        except Exception as e:
            # Handle validation errors
            logger.error(f'Validation error for {file_path}: {str(e)}', exc_info=True)
            raise
    
    def _extract_function_calls(self, func_node, session, caller_name, file_path):
        """Extract function calls from a function body"""
        def find_calls(node):
            calls = []
            if node.type == 'call':
                func_expr = node.child_by_field_name('function')
                if func_expr and func_expr.type == 'identifier':
                    called_func = func_expr.text.decode('utf8')
                    calls.append(called_func)
                elif func_expr and func_expr.type == 'attribute':
                    # Handle method calls like obj.method()
                    attr = func_expr.child_by_field_name('attribute')
                    if attr:
                        called_func = attr.text.decode('utf8')
                        calls.append(called_func)
            
            for child in node.children:
                calls.extend(find_calls(child))
            return calls
        
        called_functions = find_calls(func_node)
        
        for called_func in called_functions:
            # Create CALLS relationship
            session.run(
                "MATCH (caller:Function {name: $caller, file: $file}) "
                "MERGE (called:Function {name: $called}) "
                "MERGE (caller)-[:CALLS]->(called)",
                caller=caller_name, called=called_func, file=file_path
            )

