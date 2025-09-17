import React, { useState, useCallback } from 'react';
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
import { Play, Save, Settings } from 'lucide-react';

import ComponentSidebar from './ComponentSidebar';
import PlaygroundSidebar from './PlaygroundSidebar';
import { nodeTypes } from './nodes';
import { WorkflowNode, WorkflowEdge } from '../types/workflow';

const initialNodes: Node[] = [];
const initialEdges: Edge[] = [];

const WorkflowBuilder: React.FC = () => {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [workflowName, setWorkflowName] = useState('Untitled Workflow');
  const [isPlaygroundOpen, setIsPlaygroundOpen] = useState(true);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  const handleSaveWorkflow = async () => {
    const workflow = {
      name: workflowName,
      nodes: nodes.map(node => ({
        id: node.id,
        type: node.type || 'signature_field',
        position: node.position,
        data: node.data
      })) as WorkflowNode[],
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
      const response = await fetch('/api/v1/workflows/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(workflow),
      });

      if (response.ok) {
        console.log('Workflow saved successfully');
      } else {
        console.error('Failed to save workflow');
      }
    } catch (error) {
      console.error('Error saving workflow:', error);
    }
  };

  const handleRunWorkflow = async () => {
    // TODO: Implement workflow execution
    console.log('Running workflow...');
  };

  const handleDeploy = async () => {
    // TODO: Implement deployment
    console.log('Deploying workflow...');
  };

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <input
            type="text"
            value={workflowName}
            onChange={(e) => setWorkflowName(e.target.value)}
            className="text-lg font-semibold bg-transparent border-none focus:outline-none focus:bg-gray-50 px-2 py-1 rounded"
          />
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={handleRunWorkflow}
            className="flex items-center space-x-2 px-3 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
          >
            <Play size={16} />
            <span>Run</span>
          </button>
          <button
            onClick={handleSaveWorkflow}
            className="flex items-center space-x-2 px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            <Save size={16} />
            <span>Save</span>
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
      <div className="flex flex-1">
        {/* Left Sidebar - Components */}
        <ComponentSidebar onAddNode={(nodeData) => {
          const newNode: Node = {
            id: `node-${Date.now()}`,
            type: nodeData.type,
            position: { x: 100, y: 100 },
            data: nodeData.data,
          };
          setNodes((nds) => [...nds, newNode]);
        }} />

        {/* Main Canvas */}
        <div className="flex-1 relative">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            nodeTypes={nodeTypes}
            fitView
            snapToGrid
            snapGrid={[20, 20]}
          >
            <Controls />
            <MiniMap />
            <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
          </ReactFlow>
        </div>

        {/* Right Sidebar - Playground */}
        {isPlaygroundOpen && (
          <PlaygroundSidebar
            onClose={() => setIsPlaygroundOpen(false)}
            onExecute={(inputData) => {
              console.log('Executing with input:', inputData);
              // TODO: Implement execution
            }}
          />
        )}
      </div>
    </div>
  );
};

export default WorkflowBuilder;