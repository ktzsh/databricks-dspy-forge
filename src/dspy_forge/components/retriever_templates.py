"""
Retriever component templates.

Handles UnstructuredRetrieve and StructuredRetrieve node types.
"""
import os, ast

from typing import Dict, Any
from dspy_forge.core.templates import NodeTemplate, CodeGenerationContext

from dspy.retrievers.databricks_rm import DatabricksRM

class BaseRetrieverTemplate(NodeTemplate):
    """Base template for retriever nodes"""
    
    def _extract_query(self, inputs: Dict[str, Any]) -> str:
        """Extract query from inputs"""
        query = inputs.get('query', inputs.get('question', ''))
        if not query:
            # Try to get the first string input as query
            for key, value in inputs.items():
                if isinstance(value, str) and value.strip():
                    query = value
                    break
        
        if not query:
            raise ValueError("No query found in inputs for retriever")
        
        return query


class UnstructuredRetrieveTemplate(BaseRetrieverTemplate):
    """Template for UnstructuredRetrieve nodes"""
    
    async def execute(self, inputs: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Execute UnstructuredRetrieve node"""
        query = self._extract_query(inputs)
        
        query_type = self.node_data.get('query_type', '')
        catalog_name = self.node_data.get('catalog_name', '')
        schema_name = self.node_data.get('schema_name', '')
        index_name = self.node_data.get('index_name', '')
        content_column = self.node_data.get('content_column', '')
        id_column = self.node_data.get('id_column', '')
        num_results = self.node_data.get('num_results', 3)
        score_threshold = self.node_data.get('score_threshold', 0.0)
        
        # Validate mandatory fields
        if not all([catalog_name, schema_name, index_name, content_column, id_column]):
            raise ValueError("UnstructuredRetrieve requires catalog_name, schema_name, index_name, content_column, and id_column")
        
        try:            
            # Construct full index name
            databricks_index_name = f"{catalog_name}.{schema_name}.{index_name}"
            
            # Initialize the retriever
            retriever = DatabricksRM(
                databricks_index_name=databricks_index_name,
                text_column_name=content_column,
                docs_id_column_name=id_column,
                k=num_results,
                use_with_databricks_agent_framework=False
            )
            
            # Execute retrieval
            passages = retriever(query, query_type=query_type).docs
            
            # Extract content from passages
            if hasattr(passages, 'passages'):
                # If passages is a dspy.Prediction object
                context_list = [passage for passage in passages.passages]
            elif isinstance(passages, list):
                # If passages is already a list
                context_list = passages
            else:
                # Fallback
                context_list = [str(passages)]
            
            # Apply score threshold if needed (Note: DatabricksRM may not return scores)
            # For now, we'll include all results as DatabricksRM handles relevance internally
            
            return {
                'context': context_list,  # Return as list[str] as expected by signature field
                'passages': context_list,  # Keep for backwards compatibility
                'query': query,
                'retriever_config': {
                    'databricks_index_name': databricks_index_name,
                    'text_column_name': content_column,
                    'docs_id_column_name': id_column,
                    'k': num_results,
                    'score_threshold': score_threshold
                }
            }
        except Exception as e:
            # Handle any other errors gracefully
            raise ValueError(f"UnstructuredRetrieve execution failed: {str(e)}")
    
    def generate_code(self, context: CodeGenerationContext) -> Dict[str, Any]:
        """Generate code for UnstructuredRetrieve node"""
        query_type = self.node_data.get('query_type', '')
        catalog_name = self.node_data.get('catalog_name', '')
        schema_name = self.node_data.get('schema_name', '')
        index_name = self.node_data.get('index_name', '')
        content_column = self.node_data.get('content_column', '')
        id_column = self.node_data.get('id_column', '')
        num_results = self.node_data.get('num_results', 3)

        # Get input and output fields
        input_fields = self._get_connected_fields(is_input=True)
        output_fields = self._get_connected_fields(is_input=False)
        
        instance_var = f"retriever_{context.get_node_count('unstructured_retrieve')}"
        
        # Construct full index name
        databricks_index_name = f"{catalog_name}.{schema_name}.{index_name}"
        
        # Generate instance initialization
        instance_lines = [
            f"        # Initialize DatabricksRM retriever",
            f"        self.{instance_var} = DatabricksRM(",
            f"            databricks_index_name=\"{databricks_index_name}\",",
            f"            text_column_name=\"{content_column}\",",
            f"            docs_id_column_name=\"{id_column}\",",
            f"            k={num_results},",
            f"            use_with_databricks_agent_framework=True", 
            f"        )"
        ]
        instance_lines[-1] += "\n"
        
        # Generate execution code
        forward_lines = [
            f"        # Execute UnstructuredRetrieve",
            f"        {output_fields[0]} = self.{instance_var}({input_fields[0]}, query_type='{query_type}')"
        ]
        forward_lines[-1] += "\n"
        
        instance_code = '\n'.join(instance_lines)
        forward_code = '\n'.join(forward_lines)
        
        return {
            'signature': '',
            'instance': instance_code,
            'forward': forward_code,
            'dependencies': ['from dspy.retrieve.databricks_rm import DatabricksRM'],
            'instance_var': instance_var
        }


class StructuredRetrieveTemplate(BaseRetrieverTemplate):
    """Template for StructuredRetrieve nodes"""
    
    async def execute(self, inputs: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Execute StructuredRetrieve node"""
        query = self._extract_query(inputs)
        
        genie_space_id = self.node_data.get('genie_space_id', '')
        
        # Validate mandatory fields
        if not genie_space_id:
            raise ValueError("StructuredRetrieve requires genie_space_id")
        
        try:
            # Import and initialize DatabricksGenieRM
            from dspy_forge.components.genie.databricks_genie import DatabricksGenieRM
            
            # Initialize the retriever
            retriever = DatabricksGenieRM(
                databricks_genie_space_id=genie_space_id,
                use_with_databricks_agent_framework=False
            )
            
            # Execute retrieval with Genie
            result = retriever(query)
            
            # Extract fields from the Prediction object
            context_list = result.result
            sql_query = getattr(result, 'query_sql', '')
            query_description = getattr(result, 'query_reasoning', '')
            conversation_id = getattr(result, 'conversation_id', '')

            return {
                'context': context_list,  # SQL results in markdown format
                'sql_query': sql_query,  # Generated SQL query
                'query_description': query_description,  # Description of the generated SQL query
                'conversation_id': conversation_id,  # Genie conversation ID
                'query': query,
                'retriever_config': {
                    'genie_space_id': genie_space_id,
                    'retriever_type': 'StructuredRetrieve'
                }
            }
        except Exception as e:
            # Handle any other errors gracefully
            raise ValueError(f"StructuredRetrieve execution failed: {str(e)}")

    
    def generate_code(self, context: CodeGenerationContext) -> Dict[str, Any]:
        """Generate code for StructuredRetrieve node"""
        genie_space_id = self.node_data.get('genie_space_id', '')
        
        # Get input fields
        input_fields = self._get_connected_fields(is_input=True)
        
        instance_var = f"genie_retriever_{context.get_node_count('structured_retrieve')}"
        
        # Generate instance initialization
        instance_lines = [
            f"        # Initialize DatabricksGenieRM retriever",
            f"        self.{instance_var} = DatabricksGenieRM(",
            f"            databricks_genie_space_id=\"{genie_space_id}\",",
            f"            databricks_workspace_client=self.user_authorized_client",
            f"            use_with_databricks_agent_framework=False",
            f"        )"
        ]
        instance_lines[-1] += "\n"
        
        # Generate execution code
        forward_lines = [
            f"        # Execute StructuredRetrieve",
            f"        genie_result = self.{instance_var}.forward({input_fields[0] if input_fields else 'query'})",
            f"        context = genie_result.result[0] if genie_result.result else ''",
            f"        sql_query = getattr(genie_result, 'query_sql', '')",
            f"        query_reasoning = getattr(genie_result, 'query_reasoning', '')"
        ]
        forward_lines[-1] += "\n"
        
        instance_code = '\n'.join(instance_lines)
        forward_code = '\n'.join(forward_lines)
        
        # Read DatabricksGenieRM class definition from the original file
        def _read_genie_class_definition():
            # Get the path to the databricks_genie.py file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            genie_file_path = os.path.join(current_dir, 'genie', 'databricks_genie.py')
            
            # Read the file content
            with open(genie_file_path, 'r') as f:
                file_content = f.read()
                
                # Parse the AST to extract only the class definition
                tree = ast.parse(file_content)
                
                # Find the DatabricksGenieRM class
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and node.name == 'DatabricksGenieRM':
                        # Get the source code for this class
                        class_lines = file_content.split('\n')[node.lineno-1:node.end_lineno]
                        class_definition = '\n'.join(class_lines)
                        return class_definition
                
            raise ValueError("DatabricksGenieRM class not found in databricks_genie.py")
        
        genie_class_definition = _read_genie_class_definition()

        return {
            'signature': '',
            'instance': instance_code,
            'forward': forward_code,
            'dependencies': [],
            'class_definition': genie_class_definition.strip(),
            'instance_var': instance_var
        }