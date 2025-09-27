import React, { useState, useCallback, useEffect, useRef } from 'react';
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
  useReactFlow,
  ReactFlowProvider,
} from 'reactflow';
import { Save, Settings, FolderOpen, X, Clock, ArrowRight, FileText, Hash } from 'lucide-react';

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

// Helper function to generate consistent node IDs
const generateNodeId = (): string => {
  return `node-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`;
};

// Helper function to generate consistent edge IDs
const generateEdgeId = (): string => {
  return `edge-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`;
};

// Helper function to find a good position for new nodes
const findAvailablePosition = (existingNodes: Node[], preferredX: number = 100, preferredY: number = 100) => {
  const nodeWidth = 200; // Approximate node width
  const nodeHeight = 100; // Approximate node height
  const padding = 50; // Padding between nodes
  
  // Check if position is occupied
  const isPositionOccupied = (x: number, y: number) => {
    return existingNodes.some(node => {
      const nodeX = node.position.x;
      const nodeY = node.position.y;
      return (
        x < nodeX + nodeWidth + padding &&
        x + nodeWidth + padding > nodeX &&
        y < nodeY + nodeHeight + padding &&
        y + nodeHeight + padding > nodeY
      );
    });
  };
  
  // Start with preferred position
  let x = preferredX;
  let y = preferredY;
  
  // If preferred position is occupied, find an alternative
  if (isPositionOccupied(x, y)) {
    // Try positions in a grid pattern
    let found = false;
    const maxAttempts = 50;
    let attempt = 0;
    
    for (let row = 0; row < 10 && !found && attempt < maxAttempts; row++) {
      for (let col = 0; col < 5 && !found && attempt < maxAttempts; col++) {
        x = preferredX + (col * (nodeWidth + padding));
        y = preferredY + (row * (nodeHeight + padding));
        
        if (!isPositionOccupied(x, y)) {
          found = true;
        }
        attempt++;
      }
    }
    
    // If still not found, use a random offset
    if (!found) {
      x = preferredX + Math.random() * 300;
      y = preferredY + Math.random() * 300;
    }
  }
  
  return { x, y };
};

const WorkflowBuilderContent: React.FC = () => {
  const reactFlowInstance = useReactFlow();
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Custom handler to update base nodes when enhanced nodes change
  const handleNodesChange = useCallback((changes: any[]) => {
    // Extract the base changes (removing trace data) and apply to base nodes
    onNodesChange(changes);
  }, [onNodesChange]);
  const [workflowName, setWorkflowName] = useState('Untitled Workflow');
  const [workflowId, setWorkflowId] = useState<string | null>(null);
  const [isPlaygroundOpen, setIsPlaygroundOpen] = useState(true);
  const [isWorkflowListOpen, setIsWorkflowListOpen] = useState(false);
  const [selectedNodes, setSelectedNodes] = useState<Node[]>([]);
  const [selectedEdges, setSelectedEdges] = useState<Edge[]>([]);
  const [lastExecutionResults, setLastExecutionResults] = useState<any>(null);
  const [showNodeExecutionModal, setShowNodeExecutionModal] = useState(false);
  const [selectedNodeExecution, setSelectedNodeExecution] = useState<any>(null);
  const [showDeployModal, setShowDeployModal] = useState(false);
  const [nodesWithTraceData, setNodesWithTraceData] = useState<Node[]>([]);
  const [deploymentConfig, setDeploymentConfig] = useState({
    model_name: '',
    catalog_name: '',
    schema_name: ''
  });
  const [isDeploying, setIsDeploying] = useState(false);
  const [deploymentStatus, setDeploymentStatus] = useState<any>(null);
  const [deploymentTimeoutId, setDeploymentTimeoutId] = useState<NodeJS.Timeout | null>(null);
  const { toasts, removeToast, showSuccess, showError } = useToast();
  const fitViewTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Function to ensure default start node exists and is the only start node
  const ensureDefaultStartNode = useCallback((nodes: Node[]) => {
    // Find the existing default-start-node to preserve its position
    const existingDefaultStart = nodes.find((node: Node) => node.id === 'default-start-node');
    
    // Remove all start nodes (including existing default-start-node)
    const nonStartNodes = nodes.filter((node: Node) => 
      !(node.data as any).isStart && !(node.data as any).is_start
    );
    
    // Create default start node, preserving position if it existed
    const defaultStart = existingDefaultStart 
      ? { ...createDefaultStartNode(), position: existingDefaultStart.position }
      : createDefaultStartNode();
      
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

  // Handle trace indicator click to show execution details
  const handleTraceClick = useCallback((nodeId: string, traceData: any) => {
    if (lastExecutionResults) {
      const node = nodes.find(n => n.id === nodeId);
      if (node) {
        setSelectedNodeExecution({
          node,
          execution: traceData,
          nodeOutput: lastExecutionResults.node_outputs[nodeId]
        });
        setShowNodeExecutionModal(true);
      }
    }
  }, [lastExecutionResults, nodes]);

  // Update nodes with trace data when execution results change
  useEffect(() => {
    if (lastExecutionResults && lastExecutionResults.execution_trace) {
      const enhancedNodes = nodes.map(node => {
        const traceData = lastExecutionResults.execution_trace.find(
          (trace: any) => trace.node_id === node.id
        );

        if (traceData) {
          return {
            ...node,
            data: {
              ...node.data,
              traceData,
              onTraceClick: handleTraceClick
            }
          };
        }

        // Remove trace data if no longer available
        const { traceData: _, onTraceClick: __, ...cleanData } = node.data || {};
        return {
          ...node,
          data: cleanData
        };
      });

      setNodesWithTraceData(enhancedNodes);
    } else {
      // Remove trace data from all nodes
      const cleanNodes = nodes.map(node => {
        const { traceData: _, onTraceClick: __, ...cleanData } = node.data || {};
        return {
          ...node,
          data: cleanData
        };
      });
      setNodesWithTraceData(cleanNodes);
    }
  }, [nodes, lastExecutionResults, handleTraceClick]);

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

  // Cleanup timeouts on unmount
  useEffect(() => {
    return () => {
      if (fitViewTimeoutRef.current) {
        clearTimeout(fitViewTimeoutRef.current);
      }
      if (deploymentTimeoutId) {
        clearTimeout(deploymentTimeoutId);
      }
    };
  }, [deploymentTimeoutId]);

  const handleLoadWorkflow = useCallback((workflow: any) => {
    // Convert backend data to frontend format
    const loadedNodes = workflow.nodes.map((node: any) => {
      let nodeData = { ...node.data };
      
      // Convert snake_case back to camelCase for frontend
      if (node.data.module_type) {
        nodeData.moduleType = node.data.module_type;
        delete nodeData.module_type;
      }
      
      if (node.data.logic_type) {
        nodeData.logicType = node.data.logic_type;
        delete nodeData.logic_type;
      }

      // Convert logic node specific fields
      if (node.data.selected_fields) {
        nodeData.selectedFields = node.data.selected_fields;
        delete nodeData.selected_fields;
      }

      if (node.data.field_mappings) {
        nodeData.fieldMappings = node.data.field_mappings;
        delete nodeData.field_mappings;
      }
      
      if (node.data.retriever_type) {
        nodeData.retrieverType = node.data.retriever_type;
        delete nodeData.retriever_type;
      }
      
      // Convert other snake_case fields back to camelCase for retrievers
      const snakeToCamelMappings = {
        catalog_name: 'catalogName',
        schema_name: 'schemaName',
        index_name: 'indexName',
        content_column: 'contentColumn',
        id_column: 'idColumn',
        embedding_model: 'embeddingModel',
        query_type: 'queryType',
        num_results: 'numResults',
        score_threshold: 'scoreThreshold',
        genie_space_id: 'genieSpaceId'
      };
      
      for (const [snakeCase, camelCase] of Object.entries(snakeToCamelMappings)) {
        if (nodeData[snakeCase] !== undefined) {
          nodeData[camelCase] = nodeData[snakeCase];
          delete nodeData[snakeCase];
        }
      }
      
      return {
        id: node.id,
        type: node.type || 'signature_field',
        position: node.position || { x: 100, y: 100 },
        data: nodeData
      };
    });

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
    
    // Auto-fit view after loading with a slight delay to ensure nodes are rendered
    if (fitViewTimeoutRef.current) {
      clearTimeout(fitViewTimeoutRef.current);
    }
    fitViewTimeoutRef.current = setTimeout(() => {
      reactFlowInstance.fitView({ 
        padding: 0.1, 
        duration: 800,
        minZoom: 0.3,
        maxZoom: 1.2
      });
    }, 100);
  }, [setNodes, setEdges, ensureDefaultStartNode, reactFlowInstance]);

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
        
        if (node.type === 'logic') {
          // Convert logicType to logic_type
          if (nodeData.logicType) {
            nodeData.logic_type = nodeData.logicType;
            delete nodeData.logicType;
          }

          // Convert selectedFields to selected_fields
          if (nodeData.selectedFields) {
            nodeData.selected_fields = nodeData.selectedFields;
            delete nodeData.selectedFields;
          }

          // Convert fieldMappings to field_mappings
          if (nodeData.fieldMappings) {
            nodeData.field_mappings = nodeData.fieldMappings;
            delete nodeData.fieldMappings;
          }
        }
        
        if (node.type === 'retriever') {
          // Convert retrieverType to retriever_type
          if (nodeData.retrieverType) {
            nodeData.retriever_type = nodeData.retrieverType;
            delete nodeData.retrieverType;
          }
          
          // Convert other camelCase fields for retrievers
          const camelToSnakeMappings = {
            catalogName: 'catalog_name',
            schemaName: 'schema_name',
            indexName: 'index_name',
            contentColumn: 'content_column',
            idColumn: 'id_column',
            embeddingModel: 'embedding_model',
            queryType: 'query_type',
            numResults: 'num_results',
            scoreThreshold: 'score_threshold',
            genieSpaceId: 'genie_space_id'
          };
          
          for (const [camelCase, snakeCase] of Object.entries(camelToSnakeMappings)) {
            if (nodeData[camelCase] !== undefined) {
              nodeData[snakeCase] = nodeData[camelCase];
              delete nodeData[camelCase];
            }
          }
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
    if (!workflowId) {
      showError('Save Required', 'Please save your workflow before deploying.');
      return;
    }
    setShowDeployModal(true);
  };

  const handleDeploySubmit = async () => {
    if (!deploymentConfig.model_name || !deploymentConfig.catalog_name || !deploymentConfig.schema_name) {
      showError('Missing Information', 'Please fill in all deployment fields.');
      return;
    }

    setIsDeploying(true);
    setDeploymentStatus(null);

    try {
      const response = await fetch(`/api/v1/workflows/deploy/${workflowId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(deploymentConfig),
      });

      if (response.ok) {
        const deploymentResult = await response.json();
        setDeploymentStatus(deploymentResult);
        showSuccess('Deployment Started', 'Your workflow deployment has started. You can track the progress below.');
        
        // Poll for deployment status
        pollDeploymentStatus(deploymentResult.deployment_id);
      } else {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData.detail || 'Failed to start deployment';
        showError('Deployment Failed', errorMessage);
        setIsDeploying(false);
      }
    } catch (error) {
      showError('Network Error', 'Unable to start deployment. Please check your connection and try again.');
      console.error('Error starting deployment:', error);
      setIsDeploying(false);
    }
  };

  const pollDeploymentStatus = async (deploymentId: string) => {
    const maxAttempts = 60; // Poll for up to 10 minutes (10s intervals)
    let attempts = 0;
    let consecutiveErrors = 0;
    const maxConsecutiveErrors = 3;

    const poll = async () => {
      if (attempts >= maxAttempts) {
        showError('Deployment Timeout', 'Deployment is taking longer than expected. Please check manually.');
        setIsDeploying(false);
        return;
      }

      if (consecutiveErrors >= maxConsecutiveErrors) {
        showError('Deployment Error', 'Unable to check deployment status. Please check manually.');
        setIsDeploying(false);
        return;
      }

      try {
        const response = await fetch(`/api/v1/workflows/deploy/status/${deploymentId}`);
        
        if (response.ok) {
          consecutiveErrors = 0; // Reset error counter on success
          const status = await response.json();
          setDeploymentStatus(status);

          if (status.status === 'completed') {
            showSuccess('Deployment Complete', 'Your workflow has been deployed successfully!');
            setIsDeploying(false);
            return;
          } else if (status.status === 'failed') {
            showError('Deployment Failed', status.message || 'Deployment failed');
            setIsDeploying(false);
            return;
          } else {
            // Continue polling for in-progress states
            attempts++;
            setTimeout(poll, 10000); // Poll every 10 seconds
          }
        } else if (response.status === 404) {
          // Deployment not found - might be too early, try again
          consecutiveErrors++;
          attempts++;
          setTimeout(poll, 5000); // Poll more frequently for 404s
        } else {
          // Other HTTP errors
          consecutiveErrors++;
          const errorData = await response.json().catch(() => ({}));
          console.error('HTTP Error polling deployment status:', response.status, errorData);
          attempts++;
          setTimeout(poll, 10000);
        }
      } catch (error) {
        consecutiveErrors++;
        console.error('Network error polling deployment status:', error);
        attempts++;
        setTimeout(poll, 10000);
      }
    };

    // Start polling after a short delay to ensure backend has time to create the deployment
    const timeoutId = setTimeout(poll, 2000);
    setDeploymentTimeoutId(timeoutId);
  };

  const cancelDeployment = () => {
    if (deploymentTimeoutId) {
      clearTimeout(deploymentTimeoutId);
      setDeploymentTimeoutId(null);
    }
    setIsDeploying(false);
    setDeploymentStatus(null);
    setShowDeployModal(false);
    showError('Deployment Cancelled', 'Deployment has been cancelled.');
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
          const newNodeId = generateNodeId();
          
          // Find an available position for the new node
          const availablePosition = findAvailablePosition(nodes, 100, 100);
          
          const newNode: Node = {
            id: newNodeId,
            type: nodeData.type,
            position: availablePosition,
            data: nodeData.data,
          };

          // Auto-connect retriever nodes to signature field with appropriate output
          if (nodeData.type === 'retriever') {
            // Create different signature fields based on retriever type
            const signatureNodeId = generateNodeId();
            let signatureFields;
            
            if (nodeData.data.retrieverType === 'StructuredRetrieve') {
              // StructuredRetrieve outputs specialized fields
              signatureFields = [
                { name: 'context', type: 'list[str]', required: true, description: 'SQL results in markdown format' },
                { name: 'sql_query', type: 'str', required: true, description: 'Generated SQL query' },
                { name: 'query_description', type: 'str', required: true, description: 'Description of the generated SQL query' }
              ];
            } else {
              // UnstructuredRetrieve outputs list of context strings
              signatureFields = [{ name: 'context', type: 'list[str]', required: true }];
            }
            
            // Find position for signature node (to the right of the retriever)
            const signaturePosition = findAvailablePosition([...nodes, newNode], availablePosition.x + 300, availablePosition.y);
            
            const signatureNode: Node = {
              id: signatureNodeId,
              type: 'signature_field',
              position: signaturePosition,
              data: {
                label: nodeData.data.retrieverType === 'StructuredRetrieve' ? 'SQL Results' : 'Retrieved Context',
                fields: signatureFields,
                isStart: false,
                isEnd: false,
                connection_mode: 'whole'
              }
            };

            // Create edge connecting retriever to signature field
            const edgeId = generateEdgeId();
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
            nodes={nodesWithTraceData}
            edges={edges}
            onNodesChange={handleNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onSelectionChange={onSelectionChange}
            nodeTypes={nodeTypes}
            defaultViewport={{ x: 0, y: 0, zoom: 0.8 }}
            minZoom={0.1}
            maxZoom={2}
            snapToGrid
            snapGrid={[20, 20]}
            deleteKeyCode={null}
            multiSelectionKeyCode={['Control', 'Meta']}
            fitViewOptions={{
              padding: 0.1,
              minZoom: 0.3,
              maxZoom: 1.2
            }}
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
              workflowIR={{ nodes, edges }}
              workflowName={workflowName}
              onClose={() => setIsPlaygroundOpen(false)}
              onExecute={(inputData) => {
                console.log('Executing with input:', inputData);
                // TODO: Implement execution
              }}
              onExecutionResults={(results) => {
                setLastExecutionResults(results);
              }}
              onSaveWorkflow={async () => {
                try {
                  // Create a modified save function that returns the ID
                  const workflow = {
                    name: workflowName,
                    nodes: nodes.map(node => {
                      // Convert frontend camelCase to backend snake_case
                      let nodeData = { ...node.data };

                      if (node.type === 'module' && nodeData.moduleType) {
                        nodeData.module_type = nodeData.moduleType;
                        delete nodeData.moduleType;
                      }

                      return {
                        id: node.id,
                        type: node.type,
                        position: node.position,
                        data: nodeData
                      };
                    }),
                    edges: edges.map(edge => ({
                      id: edge.id,
                      source: edge.source,
                      target: edge.target,
                      sourceHandle: edge.sourceHandle,
                      targetHandle: edge.targetHandle,
                      type: edge.type
                    }))
                  };

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
                    return savedWorkflow.id;
                  } else {
                    throw new Error('Failed to save workflow');
                  }
                } catch (error) {
                  console.error('Error saving workflow:', error);
                  throw error;
                }
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

      {/* Node Execution Details Modal */}
      {showNodeExecutionModal && selectedNodeExecution && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-hidden">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <div className="flex items-center space-x-3">
                <div className="flex items-center space-x-2">
                  <Hash size={16} className="text-gray-500" />
                  <span className="font-medium text-gray-900">
                    {selectedNodeExecution.node.id}
                  </span>
                </div>
                <div className="text-sm text-gray-500">
                  {selectedNodeExecution.node.type}
                </div>
                <div className="flex items-center space-x-1 text-sm text-gray-500">
                  <Clock size={12} />
                  <span>{selectedNodeExecution.execution.execution_time.toFixed(3)}s</span>
                </div>
              </div>
              <button
                onClick={() => setShowNodeExecutionModal(false)}
                className="p-1 hover:bg-gray-100 rounded"
              >
                <X size={20} className="text-gray-500" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-4 overflow-y-auto max-h-[calc(90vh-140px)]">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Inputs Section */}
                <div>
                  <div className="flex items-center space-x-2 mb-3">
                    <ArrowRight size={16} className="text-blue-500" />
                    <h3 className="font-medium text-gray-900">Inputs</h3>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3">
                    <pre className="text-sm text-gray-700 whitespace-pre-wrap">
                      {JSON.stringify(selectedNodeExecution.execution.inputs, null, 2)}
                    </pre>
                  </div>
                </div>

                {/* Outputs Section */}
                <div>
                  <div className="flex items-center space-x-2 mb-3">
                    <ArrowRight size={16} className="text-green-500" style={{ transform: 'rotate(180deg)' }} />
                    <h3 className="font-medium text-gray-900">Outputs</h3>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3">
                    <pre className="text-sm text-gray-700 whitespace-pre-wrap">
                      {JSON.stringify(selectedNodeExecution.execution.outputs, null, 2)}
                    </pre>
                  </div>
                </div>
              </div>

              {/* Additional Details */}
              <div className="mt-6">
                <div className="flex items-center space-x-2 mb-3">
                  <FileText size={16} className="text-purple-500" />
                  <h3 className="font-medium text-gray-900">Execution Details</h3>
                </div>
                <div className="bg-gray-50 rounded-lg p-3 space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Node Type:</span>
                    <span className="font-medium">{selectedNodeExecution.execution.node_type}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Execution Time:</span>
                    <span className="font-medium">{selectedNodeExecution.execution.execution_time.toFixed(3)}s</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Timestamp:</span>
                    <span className="font-medium">{new Date(selectedNodeExecution.execution.timestamp).toLocaleString()}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Deployment Modal */}
      {showDeployModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">Deploy to Databricks</h3>
              <button
                onClick={() => setShowDeployModal(false)}
                className="p-1 hover:bg-gray-100 rounded"
                disabled={isDeploying}
              >
                <X size={20} className="text-gray-500" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-4">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Model Name
                  </label>
                  <input
                    type="text"
                    value={deploymentConfig.model_name}
                    onChange={(e) => setDeploymentConfig(prev => ({ ...prev, model_name: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                    placeholder="my-workflow-model"
                    disabled={isDeploying}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Catalog Name
                  </label>
                  <input
                    type="text"
                    value={deploymentConfig.catalog_name}
                    onChange={(e) => setDeploymentConfig(prev => ({ ...prev, catalog_name: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                    placeholder="main"
                    disabled={isDeploying}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Schema Name
                  </label>
                  <input
                    type="text"
                    value={deploymentConfig.schema_name}
                    onChange={(e) => setDeploymentConfig(prev => ({ ...prev, schema_name: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                    placeholder="agents"
                    disabled={isDeploying}
                  />
                </div>

                {/* Deployment Status */}
                {deploymentStatus && (
                  <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center space-x-2 mb-2">
                      <div className={`w-3 h-3 rounded-full ${
                        deploymentStatus.status === 'completed' ? 'bg-green-500' : 
                        deploymentStatus.status === 'failed' ? 'bg-red-500' : 
                        'bg-yellow-500 animate-pulse'
                      }`}></div>
                      <span className="font-medium text-sm">{deploymentStatus.status.replace('_', ' ').toUpperCase()}</span>
                    </div>
                    <p className="text-sm text-gray-600">{deploymentStatus.message}</p>
                    {deploymentStatus.endpoint_url && (
                      <div className="mt-2">
                        <span className="text-sm font-medium text-gray-700">Endpoint URL:</span>
                        <p className="text-sm text-blue-600 break-all">{deploymentStatus.endpoint_url}</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Modal Footer */}
            <div className="flex justify-end space-x-3 p-4 border-t border-gray-200">
              {isDeploying ? (
                <>
                  <button
                    onClick={cancelDeployment}
                    className="px-4 py-2 text-red-700 bg-red-100 rounded-md hover:bg-red-200"
                  >
                    Cancel Deployment
                  </button>
                  <button
                    disabled
                    className="px-4 py-2 bg-purple-600 text-white rounded-md opacity-50 cursor-not-allowed flex items-center space-x-2"
                  >
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    <span>Deploying...</span>
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={() => setShowDeployModal(false)}
                    className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
                  >
                    Close
                  </button>
                  <button
                    onClick={handleDeploySubmit}
                    disabled={!deploymentConfig.model_name || !deploymentConfig.catalog_name || !deploymentConfig.schema_name}
                    className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Deploy
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Wrapper component with ReactFlowProvider
const WorkflowBuilder: React.FC = () => {
  return (
    <ReactFlowProvider>
      <WorkflowBuilderContent />
    </ReactFlowProvider>
  );
};

export default WorkflowBuilder;