"""
DSPy tool component templates.

Handles MCP Tool and UC Function tool types.
"""
import os
import asyncio

from typing import Dict, Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from unitycatalog.ai.core.base import set_uc_function_client
from unitycatalog.ai.core.databricks import DatabricksFunctionClient

from dspy.utils.mcp import _convert_mcp_tool_result
from dspy.adapters.types.tool import Tool, convert_input_schema_to_tool_args

from dspy_forge.core.templates import NodeTemplate, CodeGenerationContext
from dspy_forge.core.logging import get_logger

logger = get_logger(__name__)


class BaseToolTemplate(NodeTemplate):
    """Base template for tool nodes"""

    def initialize(self, context: Any):
        """
        Tools don't have a direct execution component.
        They are collected by ReAct nodes that connect to them.
        Returns None as tools are not directly executable.
        """
        return None

    def generate_code(self, context: CodeGenerationContext) -> Dict[str, Any]:
        """Generate code for tool node - handled by ReAct template"""
        # Tool nodes don't generate standalone code
        # They are collected and used by ReAct nodes
        return {
            'signature': '',
            'instance': '',
            'forward': '',
            'dependencies': [],
            'instance_var': None
        }

    def generate_tool_loading_method(self, var_prefix: str) -> str:
        """Generate method to load tools - override in subclasses"""
        raise NotImplementedError("Subclasses must implement generate_tool_loading_method")


class MCPToolTemplate(BaseToolTemplate):
    """Template for MCP Tool nodes"""

    def get_tool_config(self) -> Dict[str, Any]:
        """Extract MCP tool configuration"""
        mcp_url = self.node_data.get('mcp_url') or self.node_data.get('mcpUrl', '')
        tool_name = self.node_data.get('tool_name') or self.node_data.get('toolName') or f"MCP Server ({mcp_url})"
        
        return {
            'tool_type': 'mcp',
            'tool_name': tool_name,
            'description': self.node_data.get('description', ''),
            'mcp_url': mcp_url,
            'mcp_headers': self.node_data.get('mcp_headers') or self.node_data.get('mcpHeaders', []),
        }
    
    @staticmethod
    def convert_mcp_tool(client_info: Dict[str, Any], tool: "mcp.types.Tool") -> Tool:
        """Convert an MCP tool to DSPy Tool format"""
        args, arg_types, arg_desc = convert_input_schema_to_tool_args(tool.inputSchema)

        # Convert the MCP tool and Session to a single async method
        async def func(*args, **kwargs):
            async with streamablehttp_client(
                url=client_info["url"],
                headers=client_info["headers"]
            ) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool.name, arguments=kwargs)
                    return _convert_mcp_tool_result(result)

        return Tool(
            func=func,
            name=tool.name,
            desc=tool.description,
            args=args,
            arg_types=arg_types,
            arg_desc=arg_desc
        )

    async def list_mcp_tools(self) -> list:
        """Load MCP tools asynchronously - called during execution service setup"""
        # Get configuration
        mcp_url = self.node_data.get('mcp_url') or self.node_data.get('mcpUrl', '')
        mcp_headers = self.node_data.get('mcp_headers') or self.node_data.get('mcpHeaders', [])

        if not mcp_url:
            logger.error("MCP tool missing URL")
            return []

        # Build headers dictionary
        headers = {}
        for header in mcp_headers:
            key = header.get('key', '')
            value = header.get('value', '')
            # Support both naming conventions for headers
            is_secret = header.get('is_secret') or header.get('isSecret', False)
            env_var_name = header.get('env_var_name') or header.get('envVarName', '')

            if is_secret and env_var_name:
                # Use environment variable
                env_value = os.getenv(env_var_name)
                if env_value:
                    headers[key] = env_value
                else:
                    logger.warning(f"Environment variable {env_var_name} not found for header {key}")
            else:
                # Use literal value
                headers[key] = value

        tools = []
        try:
            async with streamablehttp_client(
                url=mcp_url,
                headers=headers
            ) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tool_list = await session.list_tools()

                    # Convert MCP tools to DSPy tools
                    tools = [
                        MCPToolTemplate.convert_mcp_tool(
                            {"url": mcp_url, "headers": headers}, tool
                        ) for tool in tool_list.tools
                    ]
            logger.info(f"Loaded {len(tools)} tools from MCP server: {mcp_url}")
        except Exception as e:
            logger.error(f"Failed to load MCP tools from {mcp_url}: {e}", exc_info=True)
            return []
        
        return tools

    def load_tools(self, context=None) -> list:
        """
        Load MCP tools - retrieves from context if pre-loaded, otherwise returns empty.
        MCP tools should be pre-loaded asynchronously by the execution service.
        """
        if context and hasattr(context, 'get_loaded_tools'):
            # Get pre-loaded tools from context
            return context.get_loaded_tools(self.node.id)

        logger.warning(f"No pre-loaded MCP tools found in context for node {self.node.id}")
        return []

    def generate_tool_loading_method(self, var_prefix: str) -> str:
        """Generate code to load all tools from MCP server"""
        tool_config = self.get_tool_config()
        mcp_url = tool_config['mcp_url']
        headers = tool_config['mcp_headers']

        # Build headers dictionary code
        header_lines = []
        header_lines.append("        headers = {")

        for header in headers:
            key = header.get('key', '')
            value = header.get('value', '')
            # Support both naming conventions
            is_secret = header.get('is_secret') or header.get('isSecret', False)
            env_var_name = header.get('env_var_name') or header.get('envVarName', '')

            if is_secret and env_var_name:
                # Use environment variable
                header_lines.append(f'            "{key}": os.getenv("{env_var_name}"),')
            else:
                # Use literal value
                header_lines.append(f'            "{key}": "{value}",')

        header_lines.append("        }")
        headers_code = '\n'.join(header_lines)

        code = f'''
    async def _load_{var_prefix}_tools(self):
        """Load all tools from MCP server: {mcp_url}"""
        import os
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

{headers_code}

        tools = []
        try:
            async with streamablehttp_client(
                url="{mcp_url}",
                headers=headers
            ) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    tool_list = await session.list_tools()
                    tools = [
                        dspy.Tool.from_mcp_tool(session, tool)
                        for tool in tool_list.tools
                    ]
        except Exception as e:
            print(f"Failed to load MCP tools from {mcp_url}: {{e}}")

        return tools
'''
        return code


class UCFunctionTemplate(BaseToolTemplate):
    """Template for Unity Catalog Function tool nodes"""

    def get_tool_config(self) -> Dict[str, Any]:
        """Extract UC function configuration"""
        # Support both snake_case (backend) and camelCase (frontend)
        catalog = self.node_data.get('catalog', '')
        schema = self.node_data.get('schema', '')
        tool_name = self.node_data.get('tool_name') or self.node_data.get('toolName') or f"UC Schema ({catalog}.{schema})"
        
        return {
            'tool_type': 'uc_function',
            'tool_name': tool_name,
            'description': self.node_data.get('description', ''),
            'catalog': catalog,
            'schema': schema,
        }

    def load_tools(self, context=None) -> list:
        """Load all Unity Catalog functions from schema"""
        from dspy_forge.utils.tool_utils import load_uc_functions_from_schema
        
        # Get configuration
        catalog = self.node_data.get('catalog', '')
        schema = self.node_data.get('schema', '')
        
        return load_uc_functions_from_schema(catalog, schema)

    def generate_tool_loading_method(self, var_prefix: str) -> str:
        """Generate code to load All functions from UC schema"""
        tool_config = self.get_tool_config()
        catalog = tool_config['catalog']
        schema = tool_config['schema']
        tool_name = tool_config['tool_name']
        
        # Generate standalone UC function loading code
        code = f'''
    def _load_{var_prefix}_tools(self):
        """Load All functions from UC schema: {catalog}.{schema}"""
        from databricks.sdk import WorkspaceClient
        from unitycatalog.ai.core.databricks import DatabricksFunctionClient
        import dspy
        
        catalog = "{catalog}"
        schema = "{schema}"
        
        try:
            # Initialize clients
            client = DatabricksFunctionClient()
            w = WorkspaceClient()
            
            # List all functions in the schema
            functions = list(w.functions.list(catalog_name=catalog, schema_name=schema))
            
            tools = []
            for func in functions:
                full_name = func.full_name or f"{{catalog}}.{{schema}}.{{func.name}}"
                
                # Extract function parameters
                args = {{}}
                arg_types = {{}}
                arg_desc = {{}}
                
                if func.input_params and func.input_params.parameters:
                    for param in func.input_params.parameters:
                        param_name = param.name
                        args[param_name] = None
                        arg_types[param_name] = param.type_name or 'string'
                        arg_desc[param_name] = param.comment or f"Parameter: {{param_name}}"
                
                # Create wrapper function with closure
                def make_wrapper(func_name):
                    def uc_function_wrapper(**kwargs):
                        try:
                            result = client.execute_function(func_name, kwargs)
                            return result
                        except Exception as e:
                            print(f"Error executing UC function {{func_name}}: {{e}}")
                            raise
                    return uc_function_wrapper
                
                # Create DSPy tool
                tool = dspy.Tool(
                    func=make_wrapper(full_name),
                    name=func.name or full_name.split('.')[-1],
                    desc=func.comment or f"Unity Catalog function: {{full_name}}",
                    args=args,
                    arg_types=arg_types,
                    arg_desc=arg_desc
                )
                tools.append(tool)
            
            return tools
            
        except Exception as e:
            print(f"Failed to load UC functions from {{catalog}}.{{schema}}: {{e}}")
            return []
'''
        return code
