import React, { useState } from 'react';
import { X, Play, MessageSquare, Loader2, AlertCircle, Trash2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface PlaygroundSidebarProps {
  workflowId: string | null;
  workflowIR: { nodes: any[]; edges: any[] } | null;
  onClose: () => void;
  onExecute: (inputData: Record<string, any>) => void;
  onExecutionResults?: (results: any) => void;
}

const PlaygroundSidebar: React.FC<PlaygroundSidebarProps> = ({ workflowId, workflowIR, onClose, onExecute, onExecutionResults }) => {
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
      // Call the playground execution endpoint with workflow IR, question, and history
      const response = await fetch('/api/v1/execution/playground', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          workflow_id: workflowId,
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
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-gray-200 flex items-center justify-between flex-shrink-0">
        <h2 className="text-lg font-semibold text-gray-900">Playground</h2>
        <div className="flex items-center space-x-2">
          {chatHistory.length > 0 && (
            <button
              onClick={clearPlayground}
              className="p-1 hover:bg-gray-100 rounded flex items-center space-x-1 text-gray-500 hover:text-gray-700"
              title="Clear conversation"
            >
              <Trash2 size={16} />
              <span className="text-sm">Clear</span>
            </button>
          )}
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded"
          >
            <X size={20} className="text-gray-500" />
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
                  className={`max-w-[80%] p-3 rounded-lg ${
                    message.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : message.role === 'system'
                      ? 'bg-yellow-100 text-yellow-800 border border-yellow-200'
                      : message.error
                      ? 'bg-red-100 text-red-800 border border-red-200'
                      : 'bg-gray-100 text-gray-900'
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
        <div className="p-4 border-t border-gray-200 bg-white flex-shrink-0">
          
          <div className="flex space-x-2">
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Enter your input here..."
              className="flex-1 p-2 border border-gray-300 rounded-md resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center"
            >
              {isExecuting ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Play size={16} />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PlaygroundSidebar;