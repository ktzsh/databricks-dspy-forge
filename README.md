# DSPy Workflow Builder

A modern drag-and-drop interface for building, running, and deploying DSPy programs. Create complex AI workflows using visual components representing DSPy signatures, modules, and logic.

## Features

- **Visual Workflow Builder**: Drag-and-drop interface for creating DSPy workflows
- **Signature-Based Components**: Design components around DSPy's signature approach
- **Flexible Type System**: Support for str, int, bool, list[str], dict, and custom Pydantic models
- **DSPy Module Integration**: Predict, ChainOfThought, ReAct, Retrieve, BestOfN, Refine
- **Logic Components**: If-Else, Merge for workflow control flow
- **Real-time Playground**: Test workflows with text and file inputs
- **Workflow Management**: Save, load, and version workflows
- **Execution Engine**: Run workflows with MLflow tracing
- **Deployment Ready**: Compile to deployable DSPy programs

## Project Structure

```
dspy-workflow-builder/
├── backend/               # FastAPI backend
│   ├── app/
│   │   ├── api/          # API endpoints
│   │   ├── core/         # Core configuration and DSPy types
│   │   ├── models/       # Pydantic models
│   │   ├── services/     # Business logic services
│   │   └── utils/        # Utility functions
│   └── requirements.txt
├── frontend/             # React frontend
│   ├── public/
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── types/        # TypeScript types
│   │   └── utils/        # Utility functions
│   └── package.json
└── README.md
```

## Quick Start

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Start the FastAPI server:
```bash
python -m app.main
```

The backend will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm start
```

The frontend will be available at `http://localhost:3000`

## Core Concepts

### Signature Fields
Define input and output data structures with types:
- **Types**: str, int, bool, float, list[str], list[int], dict, Any
- **Properties**: name, description, required/optional
- **Flow**: Can be marked as start or end nodes

### DSPy Modules
Represent DSPy's core prompting techniques:
- **Predict**: Basic prediction module
- **ChainOfThought**: Reasoning with rationale
- **ReAct**: Reasoning and acting with tools
- **Retrieve**: Information retrieval
- **BestOfN**: Multiple generations with selection
- **Refine**: Iterative refinement

### Logic Components
Control workflow execution:
- **If-Else**: Conditional branching based on field values
- **Merge**: Combine multiple execution paths

## Example Workflow

Simple RAG (Retrieval-Augmented Generation) chain:

```
START → SignatureField(question: str) 
      → Retrieve(embedding_model=sentence-transformers) 
      → SignatureField(context: list[str], question: str) 
      → ChainOfThought(lm_model=gpt-3.5-turbo) 
      → SignatureField(answer: str) → END
```

## API Endpoints

### Workflows
- `POST /api/v1/workflows/` - Create workflow
- `GET /api/v1/workflows/` - List workflows
- `GET /api/v1/workflows/{id}` - Get workflow
- `PUT /api/v1/workflows/{id}` - Update workflow
- `DELETE /api/v1/workflows/{id}` - Delete workflow

### Execution
- `POST /api/v1/execution/run/{workflow_id}` - Execute workflow
- `GET /api/v1/execution/status/{execution_id}` - Get execution status
- `GET /api/v1/execution/trace/{execution_id}` - Get execution trace

### Deployment
- `POST /api/v1/deployment/compile/{workflow_id}` - Compile workflow
- `POST /api/v1/deployment/deploy/{workflow_id}` - Deploy to Databricks
- `POST /api/v1/deployment/optimize/{workflow_id}` - Optimize workflow

## Configuration

Environment variables can be set in a `.env` file:

```env
# Workflow storage
WORKFLOWS_STORAGE_PATH=./workflows

# MLflow settings
MLFLOW_TRACKING_URI=sqlite:///mlflow.db
MLFLOW_EXPERIMENT_NAME=dspy-workflows

# Databricks settings (for deployment)
DATABRICKS_HOST=your-databricks-host
DATABRICKS_TOKEN=your-databricks-token
```

## Development Status

This project implements the core foundation for a DSPy workflow builder:

✅ **Completed**:
- Project structure and setup
- FastAPI backend with workflow CRUD operations
- React frontend with React Flow integration
- Custom node components for DSPy elements
- Basic workflow execution engine
- Component sidebar and playground interface

🚧 **In Progress**:
- MLflow tracing integration
- Workflow compiler for DSPy program generation
- Databricks deployment functionality

📋 **Planned**:
- Advanced type validation
- Tool integration for ReAct modules
- Workflow optimization features
- Real-time collaboration
- Workflow templates and marketplace

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.