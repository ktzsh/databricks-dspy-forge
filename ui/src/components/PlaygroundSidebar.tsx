import React, { useState, useEffect } from 'react';
import { X, Play, MessageSquare, Loader2, AlertCircle, Trash2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface PlaygroundSidebarProps {
  workflowId: string | null;
  workflowIR: { nodes: any[]; edges: any[] } | null;
  workflowName: string;
  onClose: () => void;
  onExecute: (inputData: Record<string, any>) => void;
  onExecutionResults?: (results: any) => void;
  onSaveWorkflow?: () => Promise<string | null>; // Returns workflowId if successful
}

const PlaygroundSidebar: React.FC<PlaygroundSidebarProps> = ({ workflowId, workflowIR, workflowName, onClose, onExecute, onExecutionResults, onSaveWorkflow }) => {
  const [inputText, setInputText] = useState('');
  const [chatHistory, setChatHistory] = useState<Array<{
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp?: string;
    execution_id?: string;
    error?: boolean;
  }>>([]);
  const [conversationHistory, setConversationHistory] = useState<Array<Record<string, any>>>([]);
  const [isExecuting, setIsExecuting] = useState(false);
  const [currentWorkflowId, setCurrentWorkflowId] = useState<string | null>(workflowId);

  // Update currentWorkflowId when workflowId prop changes
  useEffect(() => {
    setCurrentWorkflowId(workflowId);
  }, [workflowId]);

  const clearPlayground = () => {
    setChatHistory([]);
    setConversationHistory([]);
    setInputText('');
  };

  const handleExecute = async () => {
    if (!inputText.trim() || isExecuting) return;

    if (!workflowIR) {
      setChatHistory(prev => [
        ...prev,
        {
          role: 'system',
          content: 'No workflow defined. Please create a workflow first.',
          error: true,
          timestamp: new Date().toISOString()
        }
      ]);
      return;
    }

    const userInput = inputText.trim();
    const timestamp = new Date().toISOString();

    // Add user message to chat
    setChatHistory(prev => [
      ...prev,
      { role: 'user', content: userInput, timestamp }
    ]);

    setIsExecuting(true);
    setInputText('');

    try {
      let executionWorkflowId = currentWorkflowId;

      // Auto-save workflow if it doesn't have an ID yet
      if (!executionWorkflowId && onSaveWorkflow) {
        setChatHistory(prev => [
          ...prev,
          {
            role: 'system',
            content: 'Saving workflow before execution...',
            timestamp: new Date().toISOString()
          }
        ]);

        try {
          executionWorkflowId = await onSaveWorkflow();
          if (executionWorkflowId) {
            setCurrentWorkflowId(executionWorkflowId);
            setChatHistory(prev => [
              ...prev,
              {
                role: 'system',
                content: `Workflow saved successfully as "${workflowName}". Proceeding with execution...`,
                timestamp: new Date().toISOString()
              }
            ]);
          } else {
            throw new Error('Failed to save workflow');
          }
        } catch (saveError) {
          setChatHistory(prev => [
            ...prev,
            {
              role: 'system',
              content: 'Failed to save workflow. Please save manually before executing.',
              error: true,
              timestamp: new Date().toISOString()
            }
          ]);
          setIsExecuting(false);
          return;
        }
      }

      // Call the playground execution endpoint with workflow IR, question, and history
      const response = await fetch('/api/v1/execution/playground', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          workflow_id: executionWorkflowId,
          workflow_ir: workflowIR,
          question: userInput,
          conversation_history: conversationHistory
        }),
      });

      const result = await response.json();

      if (response.ok && result.success) {
        // Pass execution results to parent for node inspection
        if (onExecutionResults) {
          onExecutionResults(result);
        }
        
        // Extract all output fields from the result
        const outputFields: Record<string, any> = {};
        let responseContent = '';
        
        if (result.result && typeof result.result === 'object') {
          // Process each end node result and extract just the content values
          const resultEntries = Object.entries(result.result);
          const contentValues: string[] = [];
          
          if (resultEntries.length > 0) {
            resultEntries.forEach(([key, value]) => {
              if (typeof value === 'object' && value !== null) {
                // Extract fields from the end node result
                Object.entries(value).forEach(([fieldName, fieldValue]) => {
                  outputFields[fieldName] = fieldValue;
                });
                
                // Extract content without node name prefixes
                if ('output' in value && value.output) {
                  contentValues.push(String(value.output));
                } else if ('answer' in value && value.answer) {
                  contentValues.push(String(value.answer));
                } else if ('context' in value && value.context) {
                  contentValues.push(String(value.context));
                } else {
                  // Find the first meaningful string value
                  const meaningfulValue = Object.values(value).find(v => 
                    typeof v === 'string' && v.trim().length > 0
                  );
                  if (meaningfulValue) {
                    contentValues.push(String(meaningfulValue));
                  }
                }
              } else if (value && typeof value === 'string') {
                outputFields[key] = value;
                contentValues.push(String(value));
              }
            });
            
            // Join all content values, removing duplicates
            const uniqueContent = contentValues.filter((value, index, array) => array.indexOf(value) === index);
            responseContent = uniqueContent.join('\n\n') || 'Workflow executed successfully, but no output was generated.';
          } else {
            responseContent = 'Workflow executed successfully, but no output was generated.';
          }
        } else {
          outputFields['output'] = result.result;
          responseContent = result.result || 'Workflow executed successfully.';
        }

        // Update conversation history with the complete exchange
        const conversationExchange = {
          question: userInput,
          ...outputFields
        };
        
        setConversationHistory(prev => [...prev, conversationExchange]);

        setChatHistory(prev => [
          ...prev,
          { 
            role: 'assistant', 
            content: responseContent,
            timestamp: new Date().toISOString(),
            execution_id: result.execution_id
          }
        ]);
      } else {
        // Handle execution errors
        const errorMessage = result.error || result.detail || 'Workflow execution failed';
        setChatHistory(prev => [
          ...prev,
          { 
            role: 'assistant', 
            content: `**Execution Error**: ${errorMessage}`,
            timestamp: new Date().toISOString(),
            error: true,
            execution_id: result.execution_id
          }
        ]);
      }
    } catch (error) {
      setChatHistory(prev => [
        ...prev,
        { 
          role: 'assistant', 
          content: `**Network Error**: Unable to execute workflow. Please check your connection and try again.`,
          timestamp: new Date().toISOString(),
          error: true
        }
      ]);
    } finally {
      setIsExecuting(false);
    }

    // Call the original onExecute for any additional handling
    onExecute({ text: userInput });
  };


  return (
    <div className="h-full flex flex-col bg-white">
      <div className="bg-brand-500 px-5 py-4 flex items-center justify-between flex-shrink-0 shadow-soft-lg">
        <div>
          <h2 className="text-lg font-bold text-white">Playground</h2>
          <p className="text-xs text-brand-100">Test your workflow in real-time</p>
        </div>
        <div className="flex items-center space-x-2">
          {chatHistory.length > 0 && (
            <button
              onClick={clearPlayground}
              className="p-2 hover:bg-white/10 rounded-lg flex items-center space-x-1.5 text-white hover:text-white transition-colors"
              title="Clear conversation"
            >
              <Trash2 size={16} />
              <span className="text-sm font-medium">Clear</span>
            </button>
          )}
          <button
            onClick={onClose}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
          >
            <X size={20} className="text-white" />
          </button>
        </div>
      </div>

      <div className="flex flex-col flex-1 min-h-0">
        {/* Chat History */}
        <div className="flex-1 p-4 overflow-y-auto">
          <div className="space-y-4">
            {chatHistory.length === 0 && (
              <div className="text-center text-gray-500 py-8">
                <MessageSquare size={48} className="mx-auto mb-2 text-gray-300" />
                <p>No messages yet. Start a conversation!</p>
              </div>
            )}
            
            {chatHistory.map((message, index) => (
              <div
                key={index}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] p-3.5 rounded-2xl shadow-soft ${
                    message.role === 'user'
                      ? 'bg-brand-500 text-white'
                      : message.role === 'system'
                      ? 'bg-amber-50 text-amber-800 border border-amber-200'
                      : message.error
                      ? 'bg-coral-50 text-coral-800 border border-coral-200'
                      : 'bg-slate-100 text-slate-900'
                  }`}
                >
                  <div className="flex items-start space-x-2">
                    {message.error && (
                      <AlertCircle size={16} className="text-red-500 mt-0.5 flex-shrink-0" />
                    )}
                    <div className="flex-1">
                      <div className="markdown-content">
                        <ReactMarkdown
                          components={{
                            p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                            h1: ({ children }) => <h1 className="text-lg font-bold mb-2">{children}</h1>,
                            h2: ({ children }) => <h2 className="text-base font-bold mb-2">{children}</h2>,
                            h3: ({ children }) => <h3 className="text-sm font-bold mb-1">{children}</h3>,
                            strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                            em: ({ children }) => <em className="italic">{children}</em>,
                            code: ({ children }) => <code className="bg-gray-200 px-1 py-0.5 rounded text-xs font-mono">{children}</code>,
                            pre: ({ children }) => <pre className="bg-gray-200 p-2 rounded text-xs font-mono overflow-x-auto">{children}</pre>,
                            ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
                            ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
                            li: ({ children }) => <li className="text-sm">{children}</li>,
                            a: ({ href, children }) => <a href={href} className="text-blue-600 hover:text-blue-800 underline" target="_blank" rel="noopener noreferrer">{children}</a>,
                            blockquote: ({ children }) => <blockquote className="border-l-4 border-gray-300 pl-3 italic text-gray-700 mb-2">{children}</blockquote>
                          }}
                        >
                          {message.content}
                        </ReactMarkdown>
                      </div>
                      {message.timestamp && (
                        <div className="text-xs opacity-70 mt-2">
                          {new Date(message.timestamp).toLocaleTimeString()}
                          {message.execution_id && (
                            <span className="ml-2">ID: {message.execution_id.slice(0, 8)}</span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
            
            {/* Loading indicator */}
            {isExecuting && (
              <div className="flex justify-start">
                <div className="bg-gray-100 text-gray-900 p-3 rounded-lg">
                  <div className="flex items-center space-x-2">
                    <Loader2 size={16} className="animate-spin text-blue-500" />
                    <span>Executing workflow...</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>


        {/* Input Area */}
        <div className="p-4 border-t border-slate-200 bg-slate-50 flex-shrink-0">
          <div className="flex space-x-3">
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Type your message here..."
              className="flex-1 p-3 border border-slate-300 rounded-xl resize-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-all bg-white shadow-soft text-slate-900 placeholder-slate-400"
              rows={3}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleExecute();
                }
              }}
            />
            <button
              onClick={handleExecute}
              disabled={!inputText.trim() || isExecuting}
              className="px-5 py-2 bg-brand-500 text-white rounded-xl hover:bg-brand-600 disabled:bg-slate-300 disabled:cursor-not-allowed flex items-center justify-center transition-all shadow-soft disabled:shadow-none font-medium"
            >
              {isExecuting ? (
                <Loader2 size={18} className="animate-spin" />
              ) : (
                <Play size={18} />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PlaygroundSidebar;