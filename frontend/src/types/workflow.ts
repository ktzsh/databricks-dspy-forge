export type FieldType = 
  | 'str' 
  | 'int' 
  | 'bool' 
  | 'float' 
  | 'list[str]' 
  | 'list[int]' 
  | 'dict' 
  | 'Any';

export interface SignatureField {
  name: string;
  type: FieldType;
  description?: string;
  required: boolean;
}

export interface NodePosition {
  x: number;
  y: number;
}

export type ModuleType = 
  | 'Predict' 
  | 'ChainOfThought' 
  | 'ReAct' 
  | 'Retrieve' 
  | 'BestOfN' 
  | 'Refine';

export type LogicType = 'IfElse' | 'Merge' | 'FieldSelector';

export type NodeType = 'signature_field' | 'module' | 'logic';

export interface BaseNodeData {
  label?: string;
}

export interface SignatureFieldNodeData extends BaseNodeData {
  fields: SignatureField[];
  isStart?: boolean;
  isEnd?: boolean;
  connectionMode?: 'whole' | 'field-level'; // Toggle between connection modes
}

export interface ModuleNodeData extends BaseNodeData {
  moduleType: ModuleType;
  model?: string;
  instruction?: string; // Task description for DSPy signature
  parameters: Record<string, any>;
}

export interface LogicNodeData extends BaseNodeData {
  logicType: LogicType;
  condition?: string;
  parameters: Record<string, any>;
  // FieldSelector specific data
  selectedFields?: string[];
  fieldMappings?: Record<string, string>; // old_name -> new_name
  availableFields?: SignatureField[]; // Fields available from input
}

export interface WorkflowNode {
  id: string;
  type: NodeType;
  position: NodePosition;
  data: SignatureFieldNodeData | ModuleNodeData | LogicNodeData;
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string;
  targetHandle?: string;
  type?: string;
}

export interface Workflow {
  id: string;
  name: string;
  description?: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  createdAt: string;
  updatedAt: string;
}

export interface ExecutionResult {
  executionId: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  result?: Record<string, any>;
  error?: string;
  traceId?: string;
}