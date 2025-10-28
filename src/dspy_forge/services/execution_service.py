import os
import uuid
import tempfile

from datetime import datetime
from typing import Dict, Any, List, Optional

from dspy_forge.storage.factory import get_storage_backend
from dspy_forge.core.logging import get_logger
from dspy_forge.utils.workflow_utils import find_end_nodes
from dspy_forge.models.workflow import Workflow, WorkflowExecution
from dspy_forge.core.dspy_runtime import CompoundProgram
from dspy_forge.models.workflow import NodeType
from dspy_forge.components.tool_templates import MCPToolTemplate
from dspy_forge.components import registry  # This will auto-register all templates

logger = get_logger(__name__)

class ExecutionContext:
    """Context for workflow execution"""
    def __init__(self, workflow: Workflow, input_data: Dict[str, Any]):
        self.workflow = workflow
        self.input_data = input_data
        self.node_outputs: Dict[str, Dict[str, Any]] = {}
        self.execution_trace: List[Dict[str, Any]] = []
        self.models: Dict[str, Any] = {}
        self.node_counts: Dict[str, int] = {}  # Track count of each module type
        self.loaded_tools: Dict[str, List[Any]] = {}  # Store pre-loaded tools by node_id

    def set_node_output(self, node_id: str, output: Dict[str, Any]):
        """Set output for a node"""
        self.node_outputs[node_id] = output

    def get_node_output(self, node_id: str) -> Dict[str, Any]:
        """Get output from a node"""
        return self.node_outputs.get(node_id, {})

    def set_loaded_tools(self, node_id: str, tools: List[Any]):
        """Store pre-loaded tools for a tool node"""
        self.loaded_tools[node_id] = tools

    def get_loaded_tools(self, node_id: str) -> List[Any]:
        """Get pre-loaded tools for a tool node"""
        return self.loaded_tools.get(node_id, [])
        
    def add_trace_entry(self, node_id: str, node_type: str, inputs: Dict[str, Any], outputs: Dict[str, Any], execution_time: float):
        """Add entry to execution trace"""
        self.execution_trace.append({
            'node_id': node_id,
            'node_type': node_type,
            'inputs': inputs,
            'outputs': outputs,
            'execution_time': execution_time,
            'timestamp': datetime.now().isoformat()
        })


class WorkflowExecutionEngine:
    """Engine for executing DSPy workflows"""
    
    def __init__(self):
        self.active_executions: Dict[str, WorkflowExecution] = {}
    
    async def execute_workflow(self, workflow: Workflow, input_data: Dict[str, Any], global_tools_config: Dict[str, Any] = None) -> WorkflowExecution:
        """Execute a workflow with given input data using CompoundProgram"""
        execution_id = str(uuid.uuid4())

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            input_data=input_data,
            execution_id=execution_id,
            status="pending"
        )

        self.active_executions[execution_id] = execution

        try:
            # Update status to running
            execution.status = "running"

            storage = await get_storage_backend()
            content = await storage.get_file(
                f"workflows/{workflow.id}/program.json")

            # Create execution context
            context = ExecutionContext(workflow, input_data)

            # Pre-load MCP tools asynchronously before creating the program
            await self._preload_mcp_tools(workflow, context)
            
            # Pre-load global tools if requested by ReAct modules
            if global_tools_config:
                await self._preload_global_tools(workflow, context, global_tools_config)

            # Create and execute CompoundProgram
            program = CompoundProgram(workflow, context)

            if content:
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json").name
                try:
                    with open(temp_file, 'w') as fh:
                        fh.write(content)
                    program.load(temp_file)
                finally:
                    os.remove(temp_file)
                logger.info(f"Loaded optimized program for workflow {workflow.id}")

            # Execute the program with input data using async forward
            await program.aforward(**input_data)

            # Get final outputs from end nodes
            end_nodes = find_end_nodes(workflow)
            final_outputs = {}
            for end_node_id in end_nodes:
                final_outputs[end_node_id] = context.get_node_output(end_node_id)

            # Include execution trace and intermediate outputs in result
            execution.result = {
                'final_outputs': final_outputs,
                'execution_trace': context.execution_trace,
                'node_outputs': context.node_outputs
            }
            execution.status = "completed"

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}", exc_info=True)
            execution.error = str(e)
            execution.status = "failed"

        return execution
    
    def get_execution_status(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get execution status"""
        return self.active_executions.get(execution_id)
    
    def get_execution_trace(self, execution_id: str) -> List[Dict[str, Any]]:
        """Get execution trace"""
        execution = self.active_executions.get(execution_id)
        if not execution:
            return []

        # For now, return empty trace - would be populated during execution
        return []

    async def _preload_mcp_tools(self, workflow: Workflow, context: ExecutionContext):
        """Pre-load MCP tools asynchronously before workflow execution"""
        # Find all MCP tool nodes
        mcp_tool_nodes = [
            node for node in workflow.nodes
            if node.type == NodeType.TOOL and
            (node.data.get('tool_type') == 'MCP_TOOL' or node.data.get('toolType') == 'MCP_TOOL')
        ]

        # Load tools for each MCP node asynchronously with error handling
        for node in mcp_tool_nodes:
            try:
                template = MCPToolTemplate(node, workflow)
                tools = await template.list_mcp_tools()
                context.set_loaded_tools(node.id, tools)
                logger.info(f"Pre-loaded {len(tools)} MCP tools for node {node.id}")
            except Exception as e:
                logger.error(f"Failed to pre-load MCP tools for node {node.id}: {e}", exc_info=True)
                context.set_loaded_tools(node.id, [])

    async def _preload_global_tools(self, workflow: Workflow, context: ExecutionContext, global_tools_config: Dict[str, Any]):
        """Pre-load global tools for ReAct modules that request them"""
        from dspy_forge.components.tool_templates import UCFunctionTemplate
        
        # Find all ReAct modules that use global tools
        react_modules = [
            node for node in workflow.nodes
            if node.type == NodeType.MODULE and
            node.data.get('module_type') == 'ReAct'
        ]
        
        global_mcp_tools = []
        global_uc_tools = []
        
        # Check if any ReAct module requests global MCP servers
        any_use_global_mcp = any(
            node.data.get('useGlobalMCPServers') or node.data.get('use_global_mcp_servers')
            for node in react_modules
        )
        
        # Check if any ReAct module requests global UC functions
        any_use_global_uc = any(
            node.data.get('useGlobalUCFunctions') or node.data.get('use_global_uc_functions')
            for node in react_modules
        )
        
        # Load global MCP tools if requested
        if any_use_global_mcp:
            mcp_servers = global_tools_config.get('mcpServers', [])
            for server_config in mcp_servers:
                try:
                    # Create a temporary tool node for loading
                    from dspy_forge.models.workflow import ToolNode, ToolNodeData
                    temp_node_data = ToolNodeData(
                        label='Global MCP',
                        tool_type='MCP_TOOL',
                        mcp_url=server_config.get('url'),
                        mcp_headers=server_config.get('headers', [])
                    )
                    temp_node = ToolNode(
                        id='global_mcp_temp',
                        type=NodeType.TOOL,
                        position={'x': 0, 'y': 0},
                        data=temp_node_data.model_dump(by_alias=True)
                    )
                    
                    template = MCPToolTemplate(temp_node, workflow)
                    all_tools = await template.list_mcp_tools()
                    
                    # Filter to only selected tools
                    selected_tool_names = set(server_config.get('selectedTools', []))
                    filtered_tools = [t for t in all_tools if t.name in selected_tool_names]
                    
                    global_mcp_tools.extend(filtered_tools)
                    logger.info(f"Loaded {len(filtered_tools)} global MCP tools from {server_config.get('url')}")
                except Exception as e:
                    logger.error(f"Failed to load global MCP tools from {server_config.get('url')}: {e}", exc_info=True)
        
        # Load global UC functions if requested
        if any_use_global_uc:
            from dspy_forge.utils.tool_utils import load_uc_functions_from_schema
            
            uc_schemas = global_tools_config.get('ucSchemas', [])
            for schema_config in uc_schemas:
                try:
                    # Use shared utility (no temporary nodes needed)
                    all_tools = load_uc_functions_from_schema(
                        schema_config.get('catalog'),
                        schema_config.get('schema')
                    )
                    
                    # Filter to only selected functions
                    selected_function_names = set(schema_config.get('selectedFunctions', []))
                    filtered_tools = [t for t in all_tools if t.name in selected_function_names]
                    
                    global_uc_tools.extend(filtered_tools)
                    logger.info(f"Loaded {len(filtered_tools)} global UC functions from {schema_config.get('catalog')}.{schema_config.get('schema')}")
                except Exception as e:
                    logger.error(f"Failed to load global UC functions from {schema_config.get('catalog')}.{schema_config.get('schema')}: {e}", exc_info=True)
        
        # Store global tools in context for ReAct modules to use
        for react_node in react_modules:
            tools_for_this_node = []
            
            if react_node.data.get('useGlobalMCPServers') or react_node.data.get('use_global_mcp_servers'):
                tools_for_this_node.extend(global_mcp_tools)
            
            if react_node.data.get('useGlobalUCFunctions') or react_node.data.get('use_global_uc_functions'):
                tools_for_this_node.extend(global_uc_tools)
            
            if tools_for_this_node:
                # Store with a special key for global tools
                context.set_loaded_tools(f"global_{react_node.id}", tools_for_this_node)
                logger.info(f"Assigned {len(tools_for_this_node)} global tools to ReAct node {react_node.id}")


# Global execution engine instance
execution_engine = WorkflowExecutionEngine()