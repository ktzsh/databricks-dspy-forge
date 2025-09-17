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
  | 'BestOfN' 
  | 'Refine';

export type RetrieverType = 'UnstructuredRetrieve';

export type LogicType = 'IfElse' | 'Merge' | 'FieldSelector';

export type NodeType = 'signature_field' | 'module' | 'logic' | 'retriever';

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

export interface RetrieverNodeData extends BaseNodeData {
  retrieverType: RetrieverType;
  catalogName: string; // Mandatory
  schemaName: string; // Mandatory
  indexName: string; // Mandatory
  embeddingModel?: string; // Optional
  queryType: 'HYBRID' | 'ANN'; // Default HYBRID
  numResults: number; // Default 3
  scoreThreshold?: number; // Default 0.0
  parameters: Record<string, any>;
}

export interface WorkflowNode {
  id: string;
  type: NodeType;
  position: NodePosition;
  data: SignatureFieldNodeData | ModuleNodeData | LogicNodeData | RetrieverNodeData;
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