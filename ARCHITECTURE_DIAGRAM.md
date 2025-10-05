# DSPy Forge Architecture Diagram

## New Execution Flow with CompoundProgram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Playground API Request                       │
│                 /api/v1/execution/playground                     │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│              WorkflowExecutionEngine.execute_workflow()          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  1. Create ExecutionContext(workflow, input_data)         │  │
│  │  2. Create CompoundProgram(workflow, context)             │  │
│  │  3. Execute: program.forward(**input_data)                │  │
│  │  4. Extract final outputs from context                    │  │
│  │  5. Return WorkflowExecution with results & traces        │  │
│  └───────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CompoundProgram (dspy.Module)                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  __init__(workflow, context):                             │  │
│  │    • Parse workflow structure                             │  │
│  │    • Get execution order                                  │  │
│  │    • Call _initialize_components()                        │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  _initialize_components():                                │  │
│  │    for each node in execution_order:                      │  │
│  │      template = TemplateFactory.create_template(node)     │  │
│  │      component = template.initialize(context)             │  │
│  │      if component:                                        │  │
│  │        self.components[node_id] = component               │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  forward(**inputs):                                       │  │
│  │    for each node in execution_order:                      │  │
│  │      node_inputs = _get_node_inputs(node_id, inputs)      │  │
│  │      if node_id in components:                            │  │
│  │        result = self.components[node_id](**node_inputs)   │  │
│  │      else:                                                │  │
│  │        result = template.execute(node_inputs, context)    │  │
│  │      context.set_node_output(node_id, outputs)            │  │
│  │      context.add_trace_entry(...)                         │  │
│  │    return dspy.Prediction(**final_outputs)                │  │
│  └───────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                ┌───────────────┴───────────────┐
                │                               │
                ▼                               ▼
┌─────────────────────────────┐   ┌─────────────────────────────┐
│   DSPy Module Components    │   │   Logic Components          │
│                             │   │                             │
│  • PredictTemplate          │   │  • IfElseTemplate           │
│    └─> dspy.Predict()       │   │    └─> template.execute()  │
│                             │   │                             │
│  • ChainOfThoughtTemplate   │   │  • MergeTemplate            │
│    └─> dspy.ChainOfThought()│   │    └─> template.execute()  │
│                             │   │                             │
│  • UnstructuredRetrieve     │   │  • FieldSelectorTemplate    │
│    └─> DatabricksRM()       │   │    └─> template.execute()  │
│                             │   │                             │
│  • StructuredRetrieve       │   │  • SignatureField           │
│    └─> DatabricksGenieRM()  │   │    └─> template.execute()  │
└─────────────────────────────┘   └─────────────────────────────┘
```

## Component Template Structure

```
┌────────────────────────────────────────────────────────────────┐
│                    NodeTemplate (Base Class)                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  initialize(context) -> Optional[dspy.Module]            │  │
│  │    • Returns DSPy module instance OR None                │  │
│  │    • Override in subclasses that need module init        │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  execute(inputs, context) -> Dict[str, Any]              │  │
│  │    • Executes node logic                                 │  │
│  │    • Required for all templates                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  generate_code(context) -> Dict[str, Any]                │  │
│  │    • Generates deployment code                           │  │
│  │    • Required for all templates                          │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
                              │
                 ┌────────────┴────────────┐
                 │                         │
                 ▼                         ▼
    ┌─────────────────────────┐  ┌─────────────────────────┐
    │   Module Templates      │  │   Logic Templates       │
    │                         │  │                         │
    │  ✓ initialize() → DSPy  │  │  ✗ initialize() → None  │
    │  ✓ execute()            │  │  ✓ execute()            │
    │  ✓ generate_code()      │  │  ✓ generate_code()      │
    └─────────────────────────┘  └─────────────────────────┘
```

## Data Flow Through Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                          Input Data                              │
│                    { question: "...", ... }                      │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Start Signature Field Node                    │
│                     (No execution, just passthrough)             │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                ┌───────────────┴───────────────┐
                │                               │
                ▼                               ▼
    ┌─────────────────────┐         ┌─────────────────────┐
    │   Retriever Node    │         │   Module Node       │
    │                     │         │                     │
    │  Input: question    │         │  Input: question    │
    │  Output: context    │         │  Output: answer     │
    └──────────┬──────────┘         └──────────┬──────────┘
               │                               │
               └───────────────┬───────────────┘
                               │
                               ▼
                ┌─────────────────────────────┐
                │   FieldSelector/Merge Node  │
                │                             │
                │  Input: context, answer     │
                │  Output: selected fields    │
                └──────────────┬──────────────┘
                               │
                               ▼
                ┌─────────────────────────────┐
                │     Final Module Node       │
                │                             │
                │  Input: selected fields     │
                │  Output: final_answer       │
                └──────────────┬──────────────┘
                               │
                               ▼
                ┌─────────────────────────────┐
                │    End Signature Field      │
                │                             │
                │  Output: { final_answer }   │
                └─────────────────────────────┘
```

## ExecutionContext State Management

```
┌────────────────────────────────────────────────────────────────┐
│                      ExecutionContext                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  workflow: Workflow                                      │  │
│  │    • Nodes, edges, workflow structure                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  input_data: Dict[str, Any]                              │  │
│  │    • Initial workflow inputs                             │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  node_outputs: Dict[node_id, Dict[str, Any]]             │  │
│  │    • Stores output from each executed node               │  │
│  │    • Used for input mapping to downstream nodes          │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  execution_trace: List[Dict[str, Any]]                   │  │
│  │    • Captures: node_id, inputs, outputs, timing          │  │
│  │    • Returned to UI for visualization                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  models: Dict[str, Any]                                  │  │
│  │    • Stores model configurations                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  node_counts: Dict[str, int]                             │  │
│  │    • Tracks instance count for each node type            │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

## DSPy Optimization Integration

```
┌────────────────────────────────────────────────────────────────┐
│                    Future: DSPy Optimization                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  1. Create CompoundProgram from workflow                 │  │
│  │     program = CompoundProgram(workflow, context)         │  │
│  │                                                          │  │
│  │  2. Prepare training data                                │  │
│  │     trainset = [dspy.Example(...), ...]                  │  │
│  │                                                          │  │
│  │  3. Define metric function                               │  │
│  │     def metric(example, prediction): ...                 │  │
│  │                                                          │  │
│  │  4. Create optimizer                                     │  │
│  │     optimizer = BootstrapFewShot(metric=metric)          │  │
│  │                                                          │  │
│  │  5. Compile/optimize program                             │  │
│  │     optimized = optimizer.compile(program, trainset)     │  │
│  │                                                          │  │
│  │  6. Use optimized program                                │  │
│  │     result = optimized(**inputs)                         │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

### 1. Component Initialization
- **DSPy Modules** (Predict, ChainOfThought, Retrievers):
  - Initialize in `initialize()` method
  - Stored in `CompoundProgram.components` dict
  - Executed via direct call: `component(**inputs)`

- **Logic Components** (IfElse, Merge, FieldSelector):
  - Return `None` from `initialize()`
  - Not stored in components dict
  - Executed via `template.execute()` method

### 2. Input/Output Mapping
- **Field-level connections**: Map specific fields via edge handles
- **Node-level connections**: Merge all outputs from source node
- **Start nodes**: Use initial workflow input_data
- **End nodes**: Extract from context.node_outputs

### 3. Trace Generation
- **Captured for each node**:
  - node_id, node_type
  - inputs (what went in)
  - outputs (what came out)
  - execution_time (how long it took)
  - timestamp (when it happened)

### 4. Backward Compatibility
- **Execution API**: Unchanged interface
- **Template system**: Both `initialize()` and `execute()` supported
- **Code generation**: Unaffected by changes
- **Playground API**: Works without modifications
