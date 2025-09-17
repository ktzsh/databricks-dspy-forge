import React from 'react';
import { Database, Brain, GitBranch, Filter, Search } from 'lucide-react';

interface ComponentSidebarProps {
  onAddNode: (nodeData: { type: string; data: any }) => void;
}

const ComponentSidebar: React.FC<ComponentSidebarProps> = ({ onAddNode }) => {
  const components = [
    {
      category: 'Signature Fields',
      items: [
        {
          id: 'signature-field',
          name: 'Signature Field',
          icon: Database,
          description: 'Define input/output fields with types',
          type: 'signature_field',
          data: {
            fields: [{ name: 'input', type: 'str', required: true }],
            isStart: false,
            isEnd: false
          }
        }
      ]
    },
    {
      category: 'DSPy Modules',
      items: [
        {
          id: 'predict',
          name: 'Predict',
          icon: Brain,
          description: 'Basic prediction module',
          type: 'module',
          data: {
            moduleType: 'Predict',
            model: '',
            instruction: '',
            parameters: {}
          }
        },
        {
          id: 'chain-of-thought',
          name: 'Chain of Thought',
          icon: Brain,
          description: 'Chain of thought reasoning',
          type: 'module',
          data: {
            moduleType: 'ChainOfThought',
            model: '',
            instruction: '',
            parameters: {}
          }
        },
        {
          id: 'react',
          name: 'ReAct',
          icon: Brain,
          description: 'Reasoning and acting module',
          type: 'module',
          data: {
            moduleType: 'ReAct',
            model: '',
            instruction: '',
            parameters: {}
          }
        },
        {
          id: 'best-of-n',
          name: 'Best of N',
          icon: Brain,
          description: 'Best of N selection module',
          type: 'module',
          data: {
            moduleType: 'BestOfN',
            model: '',
            instruction: '',
            parameters: {}
          }
        },
        {
          id: 'refine',
          name: 'Refine',
          icon: Brain,
          description: 'Refinement module',
          type: 'module',
          data: {
            moduleType: 'Refine',
            model: '',
            instruction: '',
            parameters: {}
          }
        }
      ]
    },
    {
      category: 'Logic Components',
      items: [
        {
          id: 'if-else',
          name: 'If-Else',
          icon: GitBranch,
          description: 'Conditional branching',
          type: 'logic',
          data: {
            logicType: 'IfElse',
            condition: '',
            parameters: {}
          }
        },
        {
          id: 'merge',
          name: 'Merge',
          icon: GitBranch,
          description: 'Merge multiple paths',
          type: 'logic',
          data: {
            logicType: 'Merge',
            parameters: {}
          }
        },
        {
          id: 'field-selector',
          name: 'Field Selector',
          icon: Filter,
          description: 'Select specific fields from input',
          type: 'logic',
          data: {
            logicType: 'FieldSelector',
            selectedFields: [],
            fieldMappings: {},
            parameters: {}
          }
        }
      ]
    },
    {
      category: 'Retrievers',
      items: [
        {
          id: 'unstructured-retrieve',
          name: 'Unstructured Retrieve',
          icon: Search,
          description: 'Databricks Vector Search',
          type: 'retriever',
          data: {
            retrieverType: 'UnstructuredRetrieve',
            catalogName: '',
            schemaName: '',
            indexName: '',
            embeddingModel: '',
            queryType: 'HYBRID',
            numResults: 3,
            scoreThreshold: 0.0,
            parameters: {}
          }
        },
        {
          id: 'structured-retrieve',
          name: 'Structured Retrieve',
          icon: Database,
          description: 'Databricks Genie Space',
          type: 'retriever',
          data: {
            retrieverType: 'StructuredRetrieve',
            genieSpaceId: '',
            parameters: {}
          }
        }
      ]
    }
  ];

  return (
    <div className="component-sidebar">
      <div className="p-4">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Components</h2>
        
        {components.map((category) => (
          <div key={category.category} className="mb-6">
            <h3 className="text-sm font-medium text-gray-700 mb-3">
              {category.category}
            </h3>
            
            <div className="space-y-2">
              {category.items.map((component) => {
                const IconComponent = component.icon;
                return (
                  <div
                    key={component.id}
                    className="p-3 bg-white border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50 hover:border-gray-300 transition-colors"
                    onClick={() => onAddNode({
                      type: component.type,
                      data: component.data
                    })}
                  >
                    <div className="flex items-center space-x-3">
                      <IconComponent size={20} className="text-gray-600" />
                      <div className="flex-1">
                        <div className="text-sm font-medium text-gray-900">
                          {component.name}
                        </div>
                        <div className="text-xs text-gray-500">
                          {component.description}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ComponentSidebar;