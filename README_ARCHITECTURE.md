
# DSPy Forge Architecture Diagram

## Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     Playground API Request                      │
│                 /api/v1/execution/playground                    │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│              WorkflowExecutionEngine.execute_workflow()         │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  1. Create ExecutionContext(workflow, input_data)         │  │
│  │  2. Create CompoundProgram(workflow, context)             │  │
│  │  3. Load optimized state if available:                    │  │
│  │     • Check storage for program.json                      │  │
│  │     • If found: program.load(program.json)                │  │
│  │     • Loads optimized prompts & few-shot examples         │  │
│  │  4. Execute: program.aforward(**input_data)               │  │
│  │  5. Extract final outputs from end nodes                  │  │
│  │  6. Return WorkflowExecution with results & traces        │  │
│  └───────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CompoundProgram (dspy.Module)                │
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
│  │  forward(**inputs):  [SYNC - for DSPy optimizers]        │  │
│  │    for each node in execution_order:                      │  │
│  │      node_inputs = _get_node_inputs(node_id, inputs)      │  │
│  │      result = self.components[node_id].call(**inputs)     │  │
│  │      context.set_node_output(node_id, outputs)            │  │
│  │      context.add_trace_entry(...)                         │  │
│  │    return dspy.Prediction(**final_outputs)                │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  aforward(**inputs):  [ASYNC - for playground/deploy]    │  │
│  │    for each node in execution_order:                      │  │
│  │      node_inputs = _get_node_inputs(node_id, inputs)      │  │
│  │      result = await self.components[node_id].acall(...)   │  │
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
│    └─> dspy.Predict()       │   │    └─> template.execute()   │
│  • ChainOfThoughtTemplate   │   │  • MergeTemplate            │
│    └─> dspy.ChainOfThought()│   │    └─> template.execute()   │
│  • ReActTemplate            │   │  • FieldSelectorTemplate    │
│    └─> dspy.ReAct()         │   │    └─> template.execute()   │
│    └─> + Tools (MCP/UC)     │   │  • SignatureField           │
│  • UnstructuredRetrieve     │   │    └─> template.execute()   │
│    └─> DatabricksRM()       │   │                             │
│  • StructuredRetrieve       │   │                             │
│    └─> DatabricksGenieRM()  │   │                             │
└─────────────────────────────┘   └─────────────────────────────┘
```


## Optimization Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                   POST /api/v1/workflows/optimize               │
│           OptimizationService.optimize_workflow_async()         │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Status: initializing                                           │
│  • Save initial status to storage backend                       │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Status: loading_data                                           │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Load datasets from Unity Catalog via SQL connector:     │  │
│  │  • Requires DATABRICKS_WAREHOUSE_ID env variable         │  │
│  │  • Query: SELECT inputs, expectations FROM {table}       │  │
│  │  • Parse inputs/expectations into dspy.Example objects   │  │
│  │  • Mark input fields with .with_inputs()                 │  │
│  │  • Load both trainset and valset                         │  │
│  └───────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Status: building_program                                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Create CompoundProgram:                                  │  │
│  │  • temp_context = ExecutionContext(workflow, {})          │  │
│  │  • program = CompoundProgram(workflow, temp_context)      │  │
│  │  • Initialize all components via template system         │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Create Composite Scoring Metric:                        │  │
│  │  • For each scoring function (Correctness/Guidelines):   │  │
│  │    - Correctness: MLflow is_correct judge                │  │
│  │    - Guidelines: MLflow meets_guidelines judge           │  │
│  │  • Weighted composite: sum(score * weightage)            │  │
│  │  • Return dspy.Prediction(score, feedback)               │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Create Optimizer Instance:                              │  │
│  │  • GEPA(metric, auto, reflection_lm)                     │  │
│  │  • BootstrapFewShotWithRandomSearch(metric, ...)         │  │
│  │  • MIPROv2(metric, auto, prompt_model, task_model)       │  │
│  └───────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Status: optimizing                                             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Run Optimization:                                        │  │
│  │  • Bootstrap/MIPROv2: optimizer.compile(program, trainset)│  │
│  │  • GEPA: optimizer.compile(program, trainset, valset)    │  │
│  │  • Returns optimized_program with updated prompts/demos  │  │
│  └───────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Status: saving_results                                         │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Save Optimized Program:                                  │  │
│  │  • Create temp directory                                  │  │
│  │  • optimized_program.save(temp_file, save_program=False) │  │
│  │  • Read program.json content                             │  │
│  │  • Save to storage: workflows/{id}/program.json          │  │
│  │  • Keys format: components['node-id']                    │  │
│  │  • Cleanup temp directory                                │  │
│  └───────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Status: completed                                              │
│  • Update status with completion timestamp                      │
│  • Include optimized_program_path in status                     │
│  • Client can now deploy or test optimized workflow             │
└─────────────────────────────────────────────────────────────────┘
```


## Deployment Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                 POST /api/v1/workflows/deploy/{id}              │
│          DeploymentService.deploy_workflow_async()              │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Status: validating                                             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Validate Workflow:                                       │  │
│  │  • Check workflow structure                               │  │
│  │  • Verify all required fields                            │  │
│  │  • Ensure valid connections                              │  │
│  │  • If validation fails, abort deployment                 │  │
│  └───────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Status: compiling                                              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Compile Workflow to DSPy Code:                          │  │
│  │  • compiler_service.compile_workflow_to_code(workflow)   │  │
│  │  • Returns: (workflow_code, node_to_var_mapping)         │  │
│  │  • Mapping example: {'node-123': 'predict_1', ...}       │  │
│  │  • Add header with workflow ID & timestamp               │  │
│  │  • Save to storage: workflows/{id}/program.py            │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Copy Agent Wrapper:                                      │  │
│  │  • Read deployment/agent.py source                        │  │
│  │  • Save to storage: workflows/{id}/agent.py              │  │
│  └───────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Transform program.json (if exists) - CRITICAL STEP             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Load Optimized State:                                    │  │
│  │  • Check for workflows/{id}/program.json                  │  │
│  │  • If not found, skip transformation                      │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Transform Keys from Node IDs → Variable Names:          │  │
│  │  • Original: {"components['node-123']": {...}}           │  │
│  │  • Transform using node_mapping from compiler            │  │
│  │  • Result: {"predict_1": {...}}                          │  │
│  │  • Keep non-component keys as-is                         │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Save Transformed State:                                  │  │
│  │  • Write to temp file: program.json                       │  │
│  │  • This file will be packaged with agent deployment      │  │
│  └───────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Generate Resource Lists & Auth Policies                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  System Resources (accessed with system credentials):    │  │
│  │  • DatabricksServingEndpoint (LLM models)                │  │
│  │  • DatabricksVectorSearchIndex (retrievers)              │  │
│  │  • DatabricksGenieSpace (structured retrievers)          │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  User Resource Scopes (OBO authentication):              │  │
│  │  • dashboards.genie (for Genie Spaces)                   │  │
│  │  • sql.warehouses (for Genie Spaces)                     │  │
│  │  • sql.statement-execution (for Genie Spaces)            │  │
│  └───────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Status: deploying                                              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Deploy to Databricks via runner.deploy_agent():        │  │
│  │  • Package files: agent.py, program.py, program.json     │  │
│  │  • mlflow.pyfunc.log_model() with:                       │  │
│  │    - python_model = agent.py                             │  │
│  │    - code_paths = [program.py]                           │  │
│  │    - artifacts = {program_state_path: program.json}      │  │
│  │    - resources = system_resources                        │  │
│  │    - auth_policy = (system, user)                        │  │
│  │  • Register model to Unity Catalog                       │  │
│  │  • Deploy to serving endpoint with agents.deploy()       │  │
│  └───────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Status: completed                                              │
│  • Update status with completion timestamp                      │
│  • Include endpoint_url and review_app_url                      │
│  • Cleanup temporary files                                      │
│  • Agent is now live and ready to serve requests                │
└─────────────────────────────────────────────────────────────────┘
```


## State Management

### ExecutionContext State Management

```
┌────────────────────────────────────────────────────────────────┐
│                      ExecutionContext                          │
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

### Program State Management

The `program.json` file is central to optimization and deployment, storing learned prompts and few-shot examples.

#### State Lifecycle

```
┌─────────────────────────────────────────────────────────────────┐
│                      OPTIMIZATION PHASE                         │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Optimizer runs on CompoundProgram                        │  │
│  │  • Updates prompts, adds few-shot demonstrations          │  │
│  │  • Learns best instruction templates                      │  │
│  │  • Stores state in program components                     │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Save with Node ID Keys:                                  │  │
│  │  • optimized_program.save(path, save_program=False)       │  │
│  │  • Format: {"components['node-123']": {...}, ...}        │  │
│  │  • Storage: workflows/{id}/program.json                   │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       EXECUTION PHASE                           │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Load Optimized State (if available):                     │  │
│  │  • program = CompoundProgram(workflow, context)           │  │
│  │  • if program.json exists:                                │  │
│  │      program.load(program.json)                           │  │
│  │  • Uses node IDs to map state to components              │  │
│  │  • Format: components['node-123'] matches workflow nodes  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DEPLOYMENT PHASE                           │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Transform for Deployment:                                │  │
│  │  • Compiler generates: (code, node_to_var_mapping)        │  │
│  │  • Example mapping: {'node-123': 'predict_1'}            │  │
│  │  • Load program.json from storage                         │  │
│  │  • Transform keys:                                        │  │
│  │      "components['node-123']" → "predict_1"              │  │
│  │  • Deployed code uses variable names, not node IDs       │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Package for Serving:                                     │  │
│  │  • agent.py loads: from program import CompoundProgram   │  │
│  │  • program.py defines: class CompoundProgram(dspy.Module)│  │
│  │  • program.json loaded via: program.load(artifacts_path) │  │
│  │  • Variable names in program.json match program.py       │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```


## Templates

### Component Templates

```
┌────────────────────────────────────────────────────────────────┐
│                    NodeTemplate (Base Class)                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  initialize(context) -> Optional[dspy.Module]            │  │
│  │    • Returns DSPy module instance OR None                │  │
│  │    • Override in subclasses that need module init        │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  call/acall(inputs, context) -> Dict[str, Any]           │  │
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
    │  ✓ call/acall()         │  │  ✓ acall/call()         │
    │  ✓ generate_code()      │  │  ✓ generate_code()      │
    └─────────────────────────┘  └─────────────────────────┘
```

### Tool Architecture

DSPy Forge supports the DSPy ReAct (Reason + Act) pattern with integrated tool support:

```
┌─────────────────────────────────────────────────────────────────┐
│                        ReAct Module                             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  dspy.ReAct(signature, tools=[...])                       │  │
│  │  • Alternates between reasoning and tool invocation       │  │
│  │  • Uses LLM to decide which tool to call                  │  │
│  │  • Iterates until final answer is reached                 │  │
│  └───────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ Tools loaded via separate handle
                             │
          ┌──────────────────┴──────────────────┐
          │                                     │
          ▼                                     ▼
┌─────────────────────────┐       ┌─────────────────────────┐
│   MCP Tool Nodes        │       │   UC Function Nodes     │
│                         │       │                         │
│  • MCP Server URL       │       │  • Catalog Name         │
│  • Custom Headers       │       │  • Schema Name          │
│  • Secret Support       │       │  • Function Name        │
│  • Async Tool Calls     │       │  • UC Client            │
└─────────────────────────┘       └─────────────────────────┘
```


## Additional Notes

### Key Transformations

| Phase | Key Format | Example | Purpose |
|-------|------------|---------|---------|
| **Optimization** | `components['node-id']` | `components['node-123']` | Maps to workflow IR node IDs |
| **Execution** | `components['node-id']` | `components['node-123']` | Same as optimization, no transform needed |
| **Deployment** | `variable_name` | `predict_1` | Maps to generated code variable names |

### Why Transformation is Needed

**During Optimization/Execution:**
- CompoundProgram uses `self.components[node_id]` to access components
- Workflow IR uses node IDs like 'node-123' to identify nodes
- program.json keys must match: `components['node-123']`

**During Deployment:**
- Generated code uses descriptive variable names: `self.predict_1`, `self.retriever_1`
- program.json must match variable names for correct state loading
- Transformation maps: `components['node-123']` → `predict_1`
