from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, List, Any, Optional, Union, Literal
from enum import Enum
from datetime import datetime


class ComparisonOperator(str, Enum):
    """Operators for condition comparisons"""
    EQ = "=="
    NE = "!="
    GT = ">"
    LT = "<"
    GTE = ">="
    LTE = "<="
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    IN = "in"
    NOT_IN = "not_in"
    STARTSWITH = "startswith"
    ENDSWITH = "endswith"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"


class LogicalOperator(str, Enum):
    """Logical operators for combining conditions"""
    AND = "AND"
    OR = "OR"


class StructuredCondition(BaseModel):
    """A single condition in structured format"""
    model_config = ConfigDict(populate_by_name=True)

    field: str
    operator: ComparisonOperator
    value: Optional[Union[str, int, float, bool, List[Any]]] = None
    logical_op: Optional[LogicalOperator] = Field(default=None, alias="logicalOp")  # For chaining to next condition


class ConditionConfig(BaseModel):
    """Configuration for If-Else conditions"""
    model_config = ConfigDict(populate_by_name=True)

    mode: Literal["structured", "expression"] = "structured"
    structured_conditions: List[StructuredCondition] = Field(default_factory=list, alias="structuredConditions")
    expression: Optional[str] = None  # For advanced expression mode


class RouterBranch(BaseModel):
    """A single branch in a Router with its own condition"""
    model_config = ConfigDict(populate_by_name=True)

    branch_id: str = Field(alias="branchId")  # Unique identifier for the branch
    label: str  # Display label for the branch
    condition_config: ConditionConfig = Field(alias="conditionConfig")  # Condition configuration for this branch
    is_default: bool = Field(default=False, alias="isDefault")  # Whether this is the default/fallback branch


class RouterConfig(BaseModel):
    """Configuration for Router logic"""
    model_config = ConfigDict(populate_by_name=True)

    branches: List[RouterBranch] = Field(default_factory=list)


class FieldType(str, Enum):
    STRING = "str"
    INTEGER = "int"
    BOOLEAN = "bool"
    FLOAT = "float"
    LIST_STRING = "list[str]"
    LIST_INT = "list[int]"
    DICT = "dict"
    ANY = "Any"
    ENUM = "enum"


class SignatureField(BaseModel):
    name: str
    type: FieldType
    description: Optional[str] = None
    required: bool = True
    enum_values: Optional[List[str]] = None  # For enum type fields


class NodePosition(BaseModel):
    x: float
    y: float


class ModuleType(str, Enum):
    PREDICT = "Predict"
    CHAIN_OF_THOUGHT = "ChainOfThought"
    REACT = "ReAct"
    BEST_OF_N = "BestOfN"
    REFINE = "Refine"


class RetrieverType(str, Enum):
    UNSTRUCTURED_RETRIEVE = "UnstructuredRetrieve"
    STRUCTURED_RETRIEVE = "StructuredRetrieve"


class LogicType(str, Enum):
    ROUTER = "Router"
    MERGE = "Merge"
    FIELD_SELECTOR = "FieldSelector"


class ToolType(str, Enum):
    MCP_TOOL = "MCP_TOOL"
    UC_FUNCTION = "UC_FUNCTION"


class NodeType(str, Enum):
    SIGNATURE_FIELD = "signature_field"
    MODULE = "module"
    LOGIC = "logic"
    RETRIEVER = "retriever"
    TOOL = "tool"


class BaseNode(BaseModel):
    id: str
    type: NodeType
    position: NodePosition
    data: Dict[str, Any]


class SignatureFieldNode(BaseNode):
    type: Literal[NodeType.SIGNATURE_FIELD] = NodeType.SIGNATURE_FIELD
    data: Dict[str, Any] = Field(default_factory=lambda: {
        "fields": [],
        "is_start": False,
        "is_end": False,
        "connection_mode": "whole"  # "whole" or "field-level"
    })


class ModuleNode(BaseNode):
    type: Literal[NodeType.MODULE] = NodeType.MODULE
    data: Dict[str, Any] = Field(default_factory=lambda: {
        "module_type": None,
        "model": None,
        "instruction": None,
        "parameters": {}
    })


class LogicNode(BaseNode):
    type: Literal[NodeType.LOGIC] = NodeType.LOGIC
    data: Dict[str, Any] = Field(default_factory=lambda: {
        "logic_type": None,
        "condition": None,  # Legacy text condition (backward compatibility)
        "router_config": None,  # Router configuration with multiple branches
        "parameters": {},
        "selected_fields": [],
        "field_mappings": {},
        "available_fields": []
    })


class RetrieverNode(BaseNode):
    type: Literal[NodeType.RETRIEVER] = NodeType.RETRIEVER
    data: Dict[str, Any] = Field(default_factory=lambda: {
        "retriever_type": None,
        # UnstructuredRetrieve fields
        "catalog_name": None,
        "schema_name": None,
        "index_name": None,
        "embedding_model": None,
        "query_type": "HYBRID",
        "num_results": 3,
        "score_threshold": 0.0,
        # StructuredRetrieve fields
        "genie_space_id": None,
        "parameters": {}
    })


class MCPHeader(BaseModel):
    """MCP Tool header configuration"""
    model_config = ConfigDict(populate_by_name=True)

    key: str
    value: str
    is_secret: bool = Field(default=False, alias="isSecret")
    env_var_name: Optional[str] = Field(default=None, alias="envVarName")


class ToolNodeData(BaseModel):
    """Tool node data with proper field aliases for camelCase/snake_case conversion"""
    model_config = ConfigDict(populate_by_name=True, extra='allow')

    tool_type: Optional[str] = Field(default=None, alias="toolType")
    tool_name: Optional[str] = Field(default=None, alias="toolName")
    description: Optional[str] = None
    # MCP Tool fields
    mcp_url: Optional[str] = Field(default=None, alias="mcpUrl")
    mcp_headers: List[Union[MCPHeader, Dict[str, Any]]] = Field(default_factory=list, alias="mcpHeaders")
    # UC Function fields
    catalog: Optional[str] = None
    schema: Optional[str] = None
    function_name: Optional[str] = Field(default=None, alias="functionName")  # Deprecated, kept for compatibility
    parameters: Dict[str, Any] = Field(default_factory=dict)
    # Base fields
    label: Optional[str] = None
    optimization_data: Optional[Dict[str, Any]] = None


class ToolNode(BaseNode):
    type: Literal[NodeType.TOOL] = NodeType.TOOL
    data: Dict[str, Any] = Field(default_factory=lambda: {
        "tool_type": None,
        "tool_name": None,
        "description": None,
        # MCP Tool fields
        "mcp_url": None,
        "mcp_headers": [],  # List of {"key": str, "value": str, "is_secret": bool, "env_var_name": str}
        # UC Function fields
        "catalog": None,
        "schema": None,
        "function_name": None,
        "parameters": {}
    })


class Edge(BaseModel):
    id: str
    source: str
    target: str
    sourceHandle: Optional[str] = None
    targetHandle: Optional[str] = None
    type: Optional[str] = "default"


class Workflow(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    description: Optional[str] = None
    nodes: List[Union[SignatureFieldNode, ModuleNode, LogicNode, RetrieverNode, ToolNode]]
    edges: List[Edge]
    created_at: datetime = Field(default_factory=datetime.now, serialization_alias="createdAt")
    updated_at: datetime = Field(default_factory=datetime.now, serialization_alias="updatedAt")


class WorkflowExecution(BaseModel):
    workflow_id: str
    input_data: Dict[str, Any]
    execution_id: str
    status: Literal["pending", "running", "completed", "failed"]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    trace_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)


class WorkflowCreateRequest(BaseModel):
    name: str
    description: str = ""
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []


class WorkflowUpdateRequest(BaseModel):
    name: str = None
    description: str = None
    nodes: List[Dict[str, Any]] = None
    edges: List[Dict[str, Any]] = None


class ExecutionRequest(BaseModel):
    input_data: Dict[str, Any]


class PlaygroundExecutionRequest(BaseModel):
    workflow_id: Optional[str] = None  # Optional workflow ID for tracking
    workflow_ir: Dict[str, Any]  # Workflow IR containing nodes and edges
    question: str
    conversation_history: list = []  # List of previous conversation exchanges
    global_tools_config: Optional[Dict[str, Any]] = None  # Global MCP/UC tools configuration


class DeploymentRequest(BaseModel):
    model_name: str
    catalog_name: str
    schema_name: str