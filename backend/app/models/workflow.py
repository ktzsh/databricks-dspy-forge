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
    RETRIEVE = "Retrieve"
    BEST_OF_N = "BestOfN"
    REFINE = "Refine"


class LogicType(str, Enum):
    IF_ELSE = "IfElse"
    MERGE = "Merge"


class NodeType(str, Enum):
    SIGNATURE_FIELD = "signature_field"
    MODULE = "module"
    LOGIC = "logic"


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
        "is_end": False
    })


class ModuleNode(BaseNode):
    type: Literal[NodeType.MODULE] = NodeType.MODULE
    data: Dict[str, Any] = Field(default_factory=lambda: {
        "module_type": None,
        "model": None,
        "parameters": {}
    })


class LogicNode(BaseNode):
    type: Literal[NodeType.LOGIC] = NodeType.LOGIC
    data: Dict[str, Any] = Field(default_factory=lambda: {
        "logic_type": None,
        "condition": None,
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
    nodes: List[Union[SignatureFieldNode, ModuleNode, LogicNode]]
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