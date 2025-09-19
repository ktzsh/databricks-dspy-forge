import React, { useState, useCallback, useEffect } from 'react';
import ReactFlow, {
  Node,
  Edge,
  addEdge,
  useNodesState,
  useEdgesState,
  Connection,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
} from 'reactflow';
import { Save, Settings, FolderOpen } from 'lucide-react';

import ComponentSidebar from './ComponentSidebar';
import PlaygroundSidebar from './PlaygroundSidebar';
import ToastContainer from './ToastContainer';
import WorkflowList from './WorkflowList';
import { nodeTypes } from './nodes';
import { WorkflowNode, WorkflowEdge } from '../types/workflow';
import { useToast } from '../hooks/useToast';

// Create the default start node (reusable function)
const createDefaultStartNode = (): Node => ({
  id: 'default-start-node',
  type: 'signature_field',
  position: { x: 100, y: 100 },
  data: {
    label: 'Input',
    fields: [
      {
        name: 'question',
        type: 'str',
        description: 'The user question or query',
        required: true
      },
      {
        name: 'history',
        type: 'list[dict[str, Any]]',
        description: 'Previous conversation history',
        required: false
      }
    ],
    isStart: true,
    connectionMode: 'whole'
  }
});

const initialNodes: Node[] = [createDefaultStartNode()];
const initialEdges: Edge[] = [];

const WorkflowBuilder: React.FC = () => {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [workflowName, setWorkflowName] = useState('Untitled Workflow');
  const [workflowId, setWorkflowId] = useState<string | null>(null);
  const [isPlaygroundOpen, setIsPlaygroundOpen] = useState(true);
  const [isWorkflowListOpen, setIsWorkflowListOpen] = useState(false);
  const [selectedNodes, setSelectedNodes] = useState<Node[]>([]);
  const [selectedEdges, setSelectedEdges] = useState<Edge[]>([]);
  const { toasts, removeToast, showSuccess, showError } = useToast();

  // Function to ensure default start node exists and is the only start node
  const ensureDefaultStartNode = useCallback((nodes: Node[]) => {
    // Remove any existing start nodes
    const nonStartNodes = nodes.filter((node: Node) => 
      !(node.data as any).isStart && !(node.data as any).is_start
    );
    
    // Add the default start node
    const defaultStart = createDefaultStartNode();
    return [defaultStart, ...nonStartNodes];
  }, []);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  // Handle selection changes (both nodes and edges)
  const onSelectionChange = useCallback(
    ({ nodes: selectedNodes, edges: selectedEdges }: { nodes: Node[]; edges: Edge[] }) => {
      setSelectedNodes(selectedNodes || []);
      setSelectedEdges(selectedEdges || []);
    },
    []
  );

  // Handle keyboard events for deletion (Delete key only, not Backspace)
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Only handle Delete key, not Backspace to prevent accidental deletions
      if (event.key === 'Delete') {
        if (selectedNodes.length > 0 || selectedEdges.length > 0) {
          event.preventDefault(); // Prevent any default browser behavior
          
          // Delete selected nodes and their connected edges
          if (selectedNodes.length > 0) {
            const selectedNodeIds = selectedNodes.map(node => node.id);
            
            // Filter out the default start node from deletion
            const deletableNodeIds = selectedNodeIds.filter(id => id !== 'default-start-node');
            
            if (deletableNodeIds.length > 0) {
              // Remove selected nodes (except default start node)
              setNodes((nds) => nds.filter(node => !deletableNodeIds.includes(node.id)));
              
              // Remove edges connected to deleted nodes
              setEdges((eds) => eds.filter(edge => 
                !deletableNodeIds.includes(edge.source) && 
                !deletableNodeIds.includes(edge.target)
              ));
            }
          }
          
          // Delete selected edges
          if (selectedEdges.length > 0) {
            const selectedEdgeIds = selectedEdges.map(edge => edge.id);
            
            // Remove selected edges
            setEdges((eds) => eds.filter(edge => !selectedEdgeIds.includes(edge.id)));
          }
          
          // Clear selections
          setSelectedNodes([]);
          setSelectedEdges([]);
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [selectedNodes, selectedEdges, setNodes, setEdges]);

  const handleLoadWorkflow = useCallback((workflow: any) => {
    // Convert backend data to frontend format
    const loadedNodes = workflow.nodes.map((node: any) => ({
      id: node.id,
      type: node.type || 'signature_field',
      position: node.position || { x: 100, y: 100 },
      data: {
        ...node.data,
        // Convert snake_case back to camelCase for frontend
        ...(node.data.module_type && { moduleType: node.data.module_type }),
        ...(node.data.logic_type && { logicType: node.data.logic_type }),
      }
    }));

    const loadedEdges = workflow.edges.map((edge: any) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      sourceHandle: edge.sourceHandle,
      targetHandle: edge.targetHandle,
      type: edge.type || 'default'
    }));

    // Ensure default start node is present and is the only start node
    const nodesWithDefaultStart = ensureDefaultStartNode(loadedNodes);

    // Update state
    setNodes(nodesWithDefaultStart);
    setEdges(loadedEdges);
    setWorkflowName(workflow.name);
    setWorkflowId(workflow.id);

    // Clear selections
    setSelectedNodes([]);
    setSelectedEdges([]);
  }, [setNodes, setEdges, ensureDefaultStartNode]);

  const handleNewWorkflow = useCallback(() => {
    const defaultStart = createDefaultStartNode();
    setNodes([defaultStart]);
    setEdges([]);
    setWorkflowName('Untitled Workflow');
    setWorkflowId(null);
    setSelectedNodes([]);
    setSelectedEdges([]);
    showSuccess('New Workflow', 'Started a new workflow with default input field');
  }, [setNodes, setEdges, showSuccess]);

  const handleSaveWorkflow = async () => {
    const workflow = {
      name: workflowName,
      nodes: nodes.map(node => {
        // Convert frontend camelCase to backend snake_case
        let nodeData = { ...node.data };
        
        if (node.type === 'module' && nodeData.moduleType) {
          nodeData.module_type = nodeData.moduleType;
          delete nodeData.moduleType;
        }
        
        if (node.type === 'logic' && nodeData.logicType) {
          nodeData.logic_type = nodeData.logicType;
          delete nodeData.logicType;
        }
        
        return {
          id: node.id,
          type: node.type || 'signature_field',
          position: node.position,
          data: nodeData
        };
      }) as WorkflowNode[],
      edges: edges.map(edge => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        sourceHandle: edge.sourceHandle,
        targetHandle: edge.targetHandle,
        type: edge.type
      })) as WorkflowEdge[]
    };

    try {
      let response;
      
      if (workflowId) {
        // Update existing workflow
        response = await fetch(`/api/v1/workflows/${workflowId}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(workflow),
        });
      } else {
        // Create new workflow
        response = await fetch('/api/v1/workflows/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(workflow),
        });
      }

      if (response.ok) {
        const savedWorkflow = await response.json();
        setWorkflowId(savedWorkflow.id);
        showSuccess(
          'Workflow Saved', 
          workflowId ? 'Your workflow has been updated successfully!' : 'Your workflow has been saved successfully!'
        );
      } else {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData.detail || 'Failed to save workflow';
        
        if (response.status === 422) {
          // Validation error
          showError('Validation Error', errorMessage);
        } else {
          // Other server errors
          showError('Save Failed', errorMessage);
        }
      }
    } catch (error) {
      showError('Network Error', 'Unable to save workflow. Please check your connection and try again.');
      console.error('Error saving workflow:', error);
    }
  };


  const handleDeploy = async () => {
    // TODO: Implement deployment
    console.log('Deploying workflow...');
  };

  return (
    <div className="h-screen flex flex-col">
      <ToastContainer toasts={toasts} onRemove={removeToast} />
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <input
            type="text"
            value={workflowName}
            onChange={(e) => setWorkflowName(e.target.value)}
            className="text-lg font-semibold bg-transparent border-none focus:outline-none focus:bg-gray-50 px-2 py-1 rounded"
          />
          {workflowId && (
            <span className="text-sm text-gray-500 bg-gray-100 px-2 py-1 rounded">
              Loaded
            </span>
          )}
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={handleNewWorkflow}
            className="flex items-center space-x-2 px-3 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
          >
            <span>New</span>
          </button>
          <button
            onClick={() => setIsWorkflowListOpen(true)}
            className="flex items-center space-x-2 px-3 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
          >
            <FolderOpen size={16} />
            <span>Load</span>
          </button>
          <button
            onClick={handleSaveWorkflow}
            className="flex items-center space-x-2 px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            <Save size={16} />
            <span>{workflowId ? 'Update' : 'Save'}</span>
          </button>
          <button
            onClick={handleDeploy}
            className="flex items-center space-x-2 px-3 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700"
          >
            <Settings size={16} />
            <span>Deploy</span>
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar - Components */}
        <div className="w-80 border-r border-gray-200 bg-gray-50 flex-shrink-0 overflow-y-auto">
          <ComponentSidebar onAddNode={(nodeData) => {
          const newNodeId = `node-${Date.now()}`;
          const newNode: Node = {
            id: newNodeId,
            type: nodeData.type,
            position: { x: 100, y: 100 },
            data: nodeData.data,
          };

          // Auto-connect retriever nodes to signature field with appropriate output
          if (nodeData.type === 'retriever') {
            // Create different signature fields based on retriever type
            const signatureNodeId = `node-${Date.now() + 1}`;
            let signatureFields;
            
            if (nodeData.data.retrieverType === 'StructuredRetrieve') {
              // StructuredRetrieve outputs specialized fields
              signatureFields = [
                { name: 'context', type: 'str', required: true, description: 'SQL results in markdown format' },
                { name: 'sql_query', type: 'str', required: true, description: 'Generated SQL query' },
                { name: 'query_description', type: 'str', required: true, description: 'Description of the generated SQL query' }
              ];
            } else {
              // UnstructuredRetrieve outputs list of context strings
              signatureFields = [{ name: 'context', type: 'list[str]', required: true }];
            }
            
            const signatureNode: Node = {
              id: signatureNodeId,
              type: 'signature_field',
              position: { x: 400, y: 100 },
              data: {
                fields: signatureFields,
                isStart: false,
                isEnd: false,
                connection_mode: 'whole'
              }
            };

            // Create edge connecting retriever to signature field
            const edgeId = `edge-${Date.now()}`;
            const newEdge: Edge = {
              id: edgeId,
              source: newNodeId,
              target: signatureNodeId,
              type: 'default'
            };

            setNodes((nds) => [...nds, newNode, signatureNode]);
            setEdges((eds) => [...eds, newEdge]);
          } else {
            setNodes((nds) => [...nds, newNode]);
          }
        }} />
        </div>

        {/* Main Canvas */}
        <div className="flex-1 relative overflow-hidden">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onSelectionChange={onSelectionChange}
            nodeTypes={nodeTypes}
            fitView
            snapToGrid
            snapGrid={[20, 20]}
            deleteKeyCode={null}
            multiSelectionKeyCode={['Control', 'Meta']}
          >
            <Controls />
            <MiniMap />
            <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
          </ReactFlow>
        </div>

        {/* Right Sidebar - Playground */}
        {isPlaygroundOpen && (
          <div className="w-96 border-l border-gray-200 bg-gray-50 flex-shrink-0 overflow-y-auto">
            <PlaygroundSidebar
              workflowId={workflowId}
              onClose={() => setIsPlaygroundOpen(false)}
              onExecute={(inputData) => {
                console.log('Executing with input:', inputData);
                // TODO: Implement execution
              }}
            />
          </div>
        )}
      </div>
      
      {/* Workflow List Modal */}
      {isWorkflowListOpen && (
        <WorkflowList
          onLoadWorkflow={handleLoadWorkflow}
          onClose={() => setIsWorkflowListOpen(false)}
        />
      )}
    </div>
  );
};

export default WorkflowBuilder;