# DSPy Workflow Builder

A modern, visual drag-and-drop interface for building, executing, and deploying DSPy programs with integrated Databricks support. Create complex AI workflows using canvas-based components representing DSPy signatures, modules, and logic flows.

## 🚀 Features

### Visual Workflow Design
- **Drag-and-Drop Canvas**: Intuitive React Flow-based interface for visual workflow creation
- **Component Library**: Pre-built nodes for DSPy signatures, modules, logic, and retrievers
- **Real-time Validation**: Live validation of workflow structure and connections
- **Interactive Playground**: Test workflows instantly with text and file inputs

### DSPy Integration
- **Core Modules**: Support for Predict, ChainOfThought, ReAct, Retrieve, BestOfN, Refine
- **Signature System**: Visual definition of input/output schemas with rich type support
- **Logic Components**: If-Else conditions and Merge operations for complex flows
- **Code Generation**: Automatic compilation to optimized DSPy programs

### Databricks Platform Integration
- **Vector Search**: Built-in UnstructuredRetrieve and StructuredRetrieve with Databricks indexes
- **Unity Catalog**: Workflow storage using Databricks Unity Catalog volumes
- **MLflow Tracking**: Execution tracing and experiment management
- **Deployment Pipeline**: One-click deployment to Databricks endpoints

### Type System & Validation
- **Rich Types**: str, int, bool, float, list[str], list[int], dict, Any, and custom Pydantic models
- **Field Properties**: Required/optional fields with descriptions and validation
- **Connection Validation**: Type-safe connections between workflow components
- **Runtime Validation**: Input/output validation during execution

## 🏗️ Architecture

```
dspy-workflow-builder/
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── api/               # REST API endpoints
│   │   │   └── endpoints/     # Workflow, execution, deployment APIs
│   │   ├── components/        # Node template system
│   │   │   ├── module_templates.py
│   │   │   └── retriever_templates.py
│   │   ├── core/              # Core configuration and DSPy types
│   │   │   ├── config.py      # Settings with Databricks config
│   │   │   └── dspy_types.py  # DSPy signature and module definitions
│   │   ├── models/            # Pydantic data models
│   │   ├── services/          # Business logic
│   │   │   ├── execution_service.py    # Workflow execution engine
│   │   │   ├── compiler_service.py     # DSPy code generation
│   │   │   └── validation_service.py   # Workflow validation
│   │   ├── storage/           # Storage backends
│   │   │   ├── local.py       # Local file storage
│   │   │   └── databricks.py  # Databricks Unity Catalog storage
│   │   └── utils/             # Utility functions
│   └── requirements.txt
├── frontend/                   # React Frontend
│   ├── src/
│   │   ├── components/        # React components
│   │   │   ├── WorkflowBuilder.tsx     # Main canvas interface
│   │   │   ├── ComponentSidebar.tsx    # Draggable component library
│   │   │   ├── PlaygroundSidebar.tsx   # Testing interface
│   │   │   └── nodes/                  # Custom node components
│   │   ├── types/             # TypeScript definitions
│   │   └── hooks/             # React hooks for state management
│   └── package.json
└── README.md
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+
- Databricks Workspace

### Backend Setup

1. **Clone and navigate to backend**:
```bash
git clone <repository>
cd dspy-workflow-builder/backend
```

2. **Create virtual environment**:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure environment** (create `.env` file):
```env
# Storage backend
STORAGE_BACKEND=local  # or "databricks"
ARTIFACTS_PATH=./artifacts/workflows

# Databricks
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=your-access-token
```

5. **Start the backend**:
```bash
python -m app.main
```

Backend available at: `http://localhost:8000`

### Frontend Setup

1. **Navigate to frontend**:
```bash
cd ../frontend
```

2. **Install dependencies**:
```bash
npm install
```

3. **Start development server**:
```bash
npm start
```

Frontend available at: `http://localhost:3000`

## 💡 Core Concepts

### Signature Fields
Define the data structures flowing through your workflow:
- **Input Fields**: Define what data enters your workflow
- **Output Fields**: Define what data exits your workflow
- **Type System**: Support for primitive types, lists, dictionaries, and custom models
- **Validation**: Required/optional fields with descriptions

### DSPy Modules
Represent core DSPy prompting and reasoning techniques:
- **Predict**: Basic prediction with language models
- **ChainOfThought**: Step-by-step reasoning with rationale
- **ReAct**: Reasoning and acting with tool integration
- **Retrieve**: Information retrieval from knowledge bases
- **BestOfN**: Generate multiple outputs and select the best
- **Refine**: Iterative improvement of outputs

### Retriever Components
Integration with Databricks vector search:
- **UnstructuredRetrieve**: Search through unstructured text documents
- **StructuredRetrieve**: Query structured data with vector similarity
- **Configuration**: Catalog, schema, index, embedding models, query types

### Logic Components
Control flow for complex workflows:
- **If-Else**: Conditional branching based on field values
- **Merge**: Combine outputs from multiple execution paths

## 🔌 API Reference

### Workflows
- `POST /api/v1/workflows/` - Create new workflow
- `GET /api/v1/workflows/` - List all workflows
- `GET /api/v1/workflows/{id}` - Get workflow details
- `PUT /api/v1/workflows/{id}` - Update workflow
- `DELETE /api/v1/workflows/{id}` - Delete workflow

### Execution
- `POST /api/v1/execution/playground` - Execute workflow in playground
- `POST /api/v1/execution/run/{workflow_id}` - Execute saved workflow
- `GET /api/v1/execution/status/{execution_id}` - Get execution status
- `GET /api/v1/execution/trace/{execution_id}` - Get detailed execution trace

### Deployment (Planned)
- `POST /api/v1/deployment/compile/{workflow_id}` - Compile to DSPy code
- `POST /api/v1/deployment/deploy/{workflow_id}` - Deploy to Databricks
- `POST /api/v1/deployment/optimize/{workflow_id}` - Optimize workflow

## 🛠️ Development

### Technology Stack
- **Backend**: FastAPI, DSPy, Pydantic, Databricks SDK
- **Frontend**: React 18, TypeScript, React Flow, TailwindCSS
- **Storage**: Local filesystem, Databricks Unity Catalog
- **Execution**: DSPy with MLflow tracing

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Support

- **Documentation**: [In-app help and tutorials]
- **Issues**: [GitHub Issues](https://github.com/your-org/dspy-workflow-builder/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/dspy-workflow-builder/discussions)

---

**Built with ❤️ for the DSPy and Databricks communities**