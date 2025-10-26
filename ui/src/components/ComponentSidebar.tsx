import React from 'react';
import { Database, Brain, GitBranch, Filter, Search, RouteIcon, AlertCircle } from 'lucide-react';

interface ComponentSidebarProps {
  onAddNode: (nodeData: { type: string; data: any }) => void;
  isDatabricksAvailable?: boolean;
}

const ComponentSidebar: React.FC<ComponentSidebarProps> = ({ onAddNode, isDatabricksAvailable = true }) => {
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
          enabled: true,
          data: {
            label: 'Signature Field',
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
          enabled: true,
          data: {
            label: 'Predict',
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
          enabled: true,
          data: {
            label: 'Chain of Thought',
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
          enabled: false,
          data: {
            label: 'ReAct',
            moduleType: 'ReAct',
            model: '',
            instruction: '',
            parameters: {}
          }
        },
        // {
        //   id: 'best-of-n',
        //   name: 'Best of N',
        //   icon: Brain,
        //   description: 'Best of N selection module',
        //   type: 'module',
        //   enabled: false,
        //   data: {
        //     label: 'Best of N',
        //     moduleType: 'BestOfN',
        //     model: '',
        //     instruction: '',
        //     parameters: {}
        //   }
        // },
        // {
        //   id: 'refine',
        //   name: 'Refine',
        //   icon: Brain,
        //   description: 'Refinement module',
        //   type: 'module',
        //   enabled: false,
        //   data: {
        //     label: 'Refine',
        //     moduleType: 'Refine',
        //     model: '',
        //     instruction: '',
        //     parameters: {}
        //   }
        // }
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
          enabled: isDatabricksAvailable,
          requiresDatabricks: true,
          data: {
            label: 'Unstructured Retrieve',
            retrieverType: 'UnstructuredRetrieve',
            catalogName: '',
            schemaName: '',
            indexName: '',
            contentColumn: '',
            idColumn: '',
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
          enabled: isDatabricksAvailable,
          requiresDatabricks: true,
          data: {
            label: 'Structured Retrieve',
            retrieverType: 'StructuredRetrieve',
            genieSpaceId: '',
            parameters: {}
          }
        }
      ]
    },
    {
      category: 'Logic Components',
      items: [
        {
          id: 'router',
          name: 'Router',
          icon: RouteIcon,
          description: 'Multi-branch conditional routing',
          type: 'logic',
          enabled: true,
          data: {
            label: 'Router',
            logicType: 'Router',
            routerConfig: {
              branches: [
                {
                  branchId: 'branch_1',
                  label: 'Branch 1',
                  conditionConfig: {
                    mode: 'structured',
                    structuredConditions: [
                      {
                        field: '',
                        operator: '==',
                        value: '',
                        logicalOp: undefined
                      }
                    ]
                  },
                  isDefault: false
                },
                {
                  branchId: 'branch_2',
                  label: 'Branch 2',
                  conditionConfig: {
                    mode: 'structured',
                    structuredConditions: [
                      {
                        field: '',
                        operator: '==',
                        value: '',
                        logicalOp: undefined
                      }
                    ]
                  },
                  isDefault: false
                }
              ]
            },
            parameters: {}
          }
        }
      ]
    }
  ];

  return (
    <div className="h-full bg-gradient-to-b from-slate-50 to-white">
      <div className="p-5">
        <div className="mb-6">
          <h2 className="text-xl font-bold text-slate-900 mb-1">Components</h2>
          <p className="text-sm text-slate-500">Drag and drop to build your workflow</p>
        </div>

        {components.map((category) => (
          <div key={category.category} className="mb-7">
            <h3 className="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-3 flex items-center">
              <span className="flex-1">{category.category}</span>
              <div className="h-px bg-slate-200 flex-1 ml-3"></div>
            </h3>

            <div className="space-y-2">
              {category.items.map((component: any) => {
                const IconComponent = component.icon;
                const isEnabled = component.enabled !== false;
                const requiresDatabricks = component.requiresDatabricks === true;
                const showDatabricksWarning = requiresDatabricks && !isDatabricksAvailable;

                return (
                  <div key={component.id}>
                    <div
                      className={`group p-3.5 bg-white border border-slate-200 rounded-xl transition-all duration-200 ${
                        isEnabled
                          ? 'cursor-pointer hover:bg-slate-50 hover:border-brand-300 hover:shadow-soft hover:scale-[1.02] active:scale-[0.98]'
                          : 'cursor-not-allowed opacity-40 grayscale'
                      }`}
                      onClick={() => {
                        if (isEnabled) {
                          onAddNode({
                            type: component.type,
                            data: component.data
                          });
                        }
                      }}
                      title={showDatabricksWarning ? 'Requires Databricks configuration' : ''}
                    >
                      <div className="flex items-center space-x-3">
                        <div className={`p-2 rounded-lg transition-colors ${
                          isEnabled
                            ? 'bg-slate-100 text-slate-700 group-hover:bg-brand-100 group-hover:text-brand-600'
                            : 'bg-slate-50 text-slate-400'
                        }`}>
                          <IconComponent size={18} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className={`text-sm font-semibold truncate ${
                            isEnabled ? "text-slate-900" : "text-slate-400"
                          }`}>
                            {component.name}
                          </div>
                          <div className={`text-xs truncate ${
                            isEnabled ? "text-slate-500" : "text-slate-300"
                          }`}>
                            {component.description}
                          </div>
                        </div>
                        {showDatabricksWarning && (
                          <AlertCircle size={14} className="text-yellow-500 flex-shrink-0" />
                        )}
                      </div>
                    </div>
                    {showDatabricksWarning && (
                      <div className="mt-1 px-2 py-1 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-700 flex items-start space-x-1">
                        <AlertCircle size={12} className="mt-0.5 flex-shrink-0" />
                        <span>Requires Databricks configuration</span>
                      </div>
                    )}
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