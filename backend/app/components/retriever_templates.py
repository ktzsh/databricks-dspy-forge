"""
Retriever component templates.

Handles UnstructuredRetrieve and StructuredRetrieve node types.
"""

from typing import Dict, Any
from app.core.templates import NodeTemplate, CodeGenerationContext


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
        
        catalog_name = self.node_data.get('catalog_name', '')
        schema_name = self.node_data.get('schema_name', '')
        index_name = self.node_data.get('index_name', '')
        embedding_model = self.node_data.get('embedding_model')
        query_type = self.node_data.get('query_type', 'HYBRID')
        num_results = self.node_data.get('num_results', 3)
        score_threshold = self.node_data.get('score_threshold', 0.0)
        
        # Validate mandatory fields
        if not all([catalog_name, schema_name, index_name]):
            raise ValueError("UnstructuredRetrieve requires catalog_name, schema_name, and index_name")
        
        # TODO: Implement actual Databricks vector search integration
        # Mock retrieval results for now
        mock_passages = [
            f"Mock retrieved passage 1 for query: {query}",
            f"Mock retrieved passage 2 for query: {query}",
            f"Mock retrieved passage 3 for query: {query}"
        ][:num_results]
        
        mock_scores = [0.95, 0.89, 0.82][:num_results]
        if score_threshold > 0:
            filtered_results = [(passage, score) for passage, score in zip(mock_passages, mock_scores) if score >= score_threshold]
            mock_passages = [p for p, s in filtered_results]
            mock_scores = [s for p, s in filtered_results]
        
        return {
            'context': mock_passages,  # Return as list[str] as expected by signature field
            'passages': mock_passages,  # Keep for backwards compatibility
            'scores': mock_scores,
            'query': query,
            'retriever_config': {
                'catalog': catalog_name,
                'schema': schema_name,
                'index': index_name,
                'embedding_model': embedding_model,
                'query_type': query_type,
                'num_results': len(mock_passages),
                'score_threshold': score_threshold
            }
        }
    
    def generate_code(self, context: CodeGenerationContext) -> Dict[str, Any]:
        """Generate code for UnstructuredRetrieve node"""
        catalog_name = self.node_data.get('catalog_name', '')
        schema_name = self.node_data.get('schema_name', '')
        index_name = self.node_data.get('index_name', '')
        embedding_model = self.node_data.get('embedding_model', '')
        query_type = self.node_data.get('query_type', 'HYBRID')
        num_results = self.node_data.get('num_results', 3)
        score_threshold = self.node_data.get('score_threshold', 0.0)
        
        instance_var = f"unstructured_retrieve_{context.get_node_count('unstructured_retrieve')}"
        
        # Generate configuration
        config_lines = [
            f"        # UnstructuredRetrieve configuration",
            f"        {instance_var}_config = {{",
            f"            'catalog_name': '{catalog_name}',",
            f"            'schema_name': '{schema_name}',",
            f"            'index_name': '{index_name}',",
            f"            'embedding_model': '{embedding_model}',",
            f"            'query_type': '{query_type}',",
            f"            'num_results': {num_results},",
            f"            'score_threshold': {score_threshold}",
            f"        }}"
        ]
        
        # Generate execution code
        forward_lines = [
            f"        # Execute UnstructuredRetrieve",
            f"        {instance_var}_result = await self._execute_unstructured_retrieve(query, {instance_var}_config)",
            f"        context = {instance_var}_result['context']",
            f"        passages = {instance_var}_result['passages']"
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