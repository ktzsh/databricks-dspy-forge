from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Union, Literal
from enum import Enum
from datetime import datetime


class FieldType(str, Enum):
    STRING = "str"
    INTEGER = "int"
    BOOLEAN = "bool"
    FLOAT = "float"
    LIST_STRING = "list[str]"
    LIST_INT = "list[int]"
    DICT = "dict"
    ANY = "Any"


class SignatureField(BaseModel):
    name: str
    type: FieldType
    description: Optional[str] = None
    required: bool = True


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
    IF_ELSE = "IfElse"
    MERGE = "Merge"
    FIELD_SELECTOR = "FieldSelector"


class NodeType(str, Enum):
    SIGNATURE_FIELD = "signature_field"
    MODULE = "module"
    LOGIC = "logic"
    RETRIEVER = "retriever"


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
        "condition": None,
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


class Edge(BaseModel):
    id: str
    source: str
    target: str
    sourceHandle: Optional[str] = None
    targetHandle: Optional[str] = None
    type: Optional[str] = "default"


class Workflow(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    nodes: List[Union[SignatureFieldNode, ModuleNode, LogicNode, RetrieverNode]]
    edges: List[Edge]
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


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
