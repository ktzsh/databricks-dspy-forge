"""
Retriever component templates.

Handles UnstructuredRetrieve and StructuredRetrieve node types.
"""

from typing import Dict, Any
from app.core.templates import NodeTemplate, CodeGenerationContext

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
            f"",
            f"        # Initialize DatabricksRM retriever",
            f"        self.{instance_var} = DatabricksRM(",
            f"            databricks_index_name=\"{databricks_index_name}\",",
            f"            text_column_name=\"{content_column}\",",
            f"            docs_id_column_name=\"{id_column}\",",
            f"            k={num_results},",
            f"            use_with_databricks_agent_framework=True", 
            f"        )"
        ]
        
        # Generate execution code
        forward_lines = [
            f"        # Execute UnstructuredRetrieve",
            f"        {output_fields[0]} = self.{instance_var}({input_fields[0]}, query_type='{query_type}')"
        ]
        
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
        
        # TODO: Implement actual Genie integration for SQL generation and execution
        # Mock SQL generation and execution results for now
        mock_sql_query = f"SELECT * FROM sales_data WHERE description LIKE '%{query}%' ORDER BY date DESC LIMIT 10;"
        mock_query_description = f"Searching for sales records related to '{query}', ordered by most recent first"
        mock_sql_results = f"""
| Date | Product | Sales | Region |
|------|---------|-------|--------|
| 2024-01-15 | Product A related to {query} | $1,500 | North |
| 2024-01-14 | Product B matching {query} | $2,300 | South |
| 2024-01-13 | Another item for {query} | $800 | East |

**Total Records Found:** 3
**Query Execution Time:** 0.45s
        """.strip()
        
        return {
            'context': mock_sql_results,  # SQL results in markdown format
            'sql_query': mock_sql_query,  # Generated SQL query
            'query_description': mock_query_description,  # Description of the generated SQL query
            'query': query,
            'retriever_config': {
                'genie_space_id': genie_space_id,
                'retriever_type': 'StructuredRetrieve'
            }
        }
    
    def generate_code(self, context: CodeGenerationContext) -> Dict[str, Any]:
        """Generate code for StructuredRetrieve node"""
        genie_space_id = self.node_data.get('genie_space_id', '')
        
        instance_var = f"structured_retrieve_{context.get_node_count('structured_retrieve')}"
        
        # Generate configuration
        config_lines = [
            f"        # StructuredRetrieve configuration",
            f"        {instance_var}_config = {{",
            f"            'genie_space_id': '{genie_space_id}'",
            f"        }}"
        ]
        
        # Generate execution code
        forward_lines = [
            f"        # Execute StructuredRetrieve",
            f"        {instance_var}_result = await self._execute_structured_retrieve(query, {instance_var}_config)",
            f"        context = {instance_var}_result['context']",
            f"        sql_query = {instance_var}_result['sql_query']"
        ]
        
        instance_code = '\n'.join(config_lines)
        forward_code = '\n'.join(forward_lines)
        
        return {
            'signature': '',
            'instance': instance_code,
            'forward': forward_code,
            'dependencies': [],
            'instance_var': instance_var
        }