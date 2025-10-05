"""
Retriever component templates.

Handles UnstructuredRetrieve and StructuredRetrieve node types.
"""
import os, ast
import dspy

from typing import Dict, Any

from dspy_forge.core.templates import NodeTemplate, CodeGenerationContext
from dspy.retrievers.databricks_rm import DatabricksRM
from dspy_forge.components.genie.databricks_genie import DatabricksGenieRM

class BaseRetrieverTemplate(NodeTemplate):
    """Base template for retriever nodes"""

    @staticmethod
    def _extract_query(inputs: Dict[str, Any]) -> str:
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

    def initialize(self, context: Any):
        """Initialize UnstructuredRetrieve component with call/acall interface"""
        self.query_type = self.node_data.get('query_type', '')

        # Initialize retriever once
        catalog_name = self.node_data.get('catalog_name', '')
        schema_name = self.node_data.get('schema_name', '')
        index_name = self.node_data.get('index_name', '')
        content_column = self.node_data.get('content_column', '')
        id_column = self.node_data.get('id_column', '')
        num_results = self.node_data.get('num_results', 3)

        if not all([catalog_name, schema_name, index_name, content_column, id_column]):
            raise ValueError("UnstructuredRetrieve requires catalog_name, schema_name, index_name, content_column, and id_column")

        databricks_index_name = f"{catalog_name}.{schema_name}.{index_name}"

        self.retriever = DatabricksRM(
            databricks_index_name=databricks_index_name,
            text_column_name=content_column,
            docs_id_column_name=id_column,
            k=num_results,
            use_with_databricks_agent_framework=False
        )
        return self

    def call(self, **inputs) -> dspy.Prediction:
        """Synchronous call for optimization"""
        query = self._extract_query(inputs)
        result = self.retriever(query, query_type=self.query_type)

        # Extract passages
        passages = result.docs
        if hasattr(passages, 'passages'):
            context_list = [passage for passage in passages.passages]
        elif isinstance(passages, list):
            context_list = passages
        else:
            context_list = [str(passages)]

        return dspy.Prediction(
            context=context_list,
            passages=context_list,
            query=query
        )

    async def acall(self, **inputs) -> dspy.Prediction:
        """Async call for playground - retrievers are sync anyway"""
        return self.call(**inputs)
    
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

    def initialize(self, context: Any):
        """Initialize StructuredRetrieve component with call/acall interface"""
        genie_space_id = self.node_data.get('genie_space_id', '')

        if not genie_space_id:
            raise ValueError("StructuredRetrieve requires genie_space_id")

        # Initialize Genie retriever once
        self.retriever = DatabricksGenieRM(
            databricks_genie_space_id=genie_space_id,
            use_with_databricks_agent_framework=False
        )
        return self

    def call(self, **inputs) -> dspy.Prediction:
        """Synchronous call for optimization"""
        query = self._extract_query(inputs)
        result = self.retriever(query)

        # Extract fields from the Prediction object
        context_list = result.result
        sql_query = getattr(result, 'query_sql', '')
        query_description = getattr(result, 'query_reasoning', '')
        conversation_id = getattr(result, 'conversation_id', '')

        return dspy.Prediction(
            context=context_list,
            sql_query=sql_query,
            query_description=query_description,
            conversation_id=conversation_id,
            query=query
        )

    async def acall(self, **inputs) -> dspy.Prediction:
        """Async call for playground - Genie is sync anyway"""
        return self.call(**inputs)
    
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
            f"            databricks_workspace_client=self.user_authorized_client,",
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