export type FieldType =
  | 'str'
  | 'int'
  | 'bool'
  | 'float'
  | 'list[str]'
  | 'list[int]'
  | 'dict'
  | 'list[dict[str, Any]]'
  | 'Any'
  | 'enum';

export interface SignatureField {
  name: string;
  type: FieldType;
  description?: string;
  required: boolean;
  enumValues?: string[];  // For enum type fields
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

export type RetrieverType = 'UnstructuredRetrieve' | 'StructuredRetrieve';

export type LogicType = 'Router' | 'Merge' | 'FieldSelector';

export type NodeType = 'signature_field' | 'module' | 'logic' | 'retriever';

export type ComparisonOperator =
  | '=='
  | '!='
  | '>'
  | '<'
  | '>='
  | '<='
  | 'contains'
  | 'not_contains'
  | 'in'
  | 'not_in'
  | 'startswith'
  | 'endswith'
  | 'is_empty'
  | 'is_not_empty';

export type LogicalOperator = 'AND' | 'OR';

export interface StructuredCondition {
  field: string;
  operator: ComparisonOperator;
  value?: string | number | boolean | any[];
  logicalOp?: LogicalOperator;
}

export interface ConditionConfig {
  mode: 'structured' | 'expression';
  structuredConditions?: StructuredCondition[];
  expression?: string;
}

export interface RouterBranch {
  branchId: string;
  label: string;
  conditionConfig: ConditionConfig;
  isDefault?: boolean;
}

export interface RouterConfig {
  branches: RouterBranch[];
}

export interface OptimizationData {
  demos: Array<Record<string, any>>;
  signature: {
    instructions: string;
    fields: Array<{
      prefix: string;
      description: string;
    }>;
  };
  has_optimization: boolean;
}

export interface BaseNodeData {
  label?: string;
  optimization_data?: OptimizationData;
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
  condition?: string;  // Legacy text condition
  routerConfig?: RouterConfig;  // Router configuration with multiple branches
  parameters: Record<string, any>;
  // FieldSelector specific data
  selectedFields?: string[];
  fieldMappings?: Record<string, string>; // old_name -> new_name
  availableFields?: SignatureField[]; // Fields available from input
}

export interface RetrieverNodeData extends BaseNodeData {
  retrieverType: RetrieverType;
  // UnstructuredRetrieve specific fields
  catalogName?: string; // Mandatory for UnstructuredRetrieve
  schemaName?: string; // Mandatory for UnstructuredRetrieve
  indexName?: string; // Mandatory for UnstructuredRetrieve
  contentColumn?: string; // Mandatory for UnstructuredRetrieve
  idColumn?: string; // Mandatory for UnstructuredRetrieve
  embeddingModel?: string; // Optional for UnstructuredRetrieve
  queryType?: 'HYBRID' | 'ANN'; // Default HYBRID for UnstructuredRetrieve
  numResults?: number; // Default 3 for UnstructuredRetrieve
  scoreThreshold?: number; // Default 0.0 for UnstructuredRetrieve
  // StructuredRetrieve specific fields
  genieSpaceId?: string; // Mandatory for StructuredRetrieve
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