import React, { useState } from 'react';
import { X, Play, Upload, MessageSquare, Loader2, AlertCircle } from 'lucide-react';

interface PlaygroundSidebarProps {
  workflowId: string | null;
  onClose: () => void;
  onExecute: (inputData: Record<string, any>) => void;
}

const PlaygroundSidebar: React.FC<PlaygroundSidebarProps> = ({ workflowId, onClose, onExecute }) => {
  const [inputText, setInputText] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [chatHistory, setChatHistory] = useState<Array<{ 
    role: 'user' | 'assistant' | 'system'; 
    content: string;
    timestamp?: string;
    execution_id?: string;
    error?: boolean;
  }>>([]);
  const [isExecuting, setIsExecuting] = useState(false);

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const uploadedFiles = Array.from(event.target.files || []);
    setFiles(prev => [...prev, ...uploadedFiles]);
  };

  const handleExecute = async () => {
    if (!inputText.trim() || isExecuting) return;
    
    if (!workflowId) {
      setChatHistory(prev => [
        ...prev,
        { 
          role: 'system', 
          content: 'Please save the workflow first before executing it in the playground.',
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
      // Prepare input data for workflow execution
      const inputData = {
        input: userInput,
        query: userInput,
        text: userInput,
        files: files.map(f => f.name)
      };

      // Call the playground execution endpoint
      const response = await fetch('/api/v1/execution/playground', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          workflow_id: workflowId,
          input_data: inputData
        }),
      });

      const result = await response.json();

      if (response.ok && result.success) {
        // Format the successful response
        let responseContent = '';
        
        if (result.result && typeof result.result === 'object') {
          // Try to extract meaningful output from the result
          const resultEntries = Object.entries(result.result);
          if (resultEntries.length > 0) {
            responseContent = resultEntries.map(([key, value]) => {
              if (typeof value === 'object' && value !== null) {
                // If the value is an object, try to extract meaningful content
                if ('output' in value) {
                  return `**${key}**: ${value.output}`;
                } else if ('context' in value) {
                  return `**${key}**: ${value.context}`;
                } else {
                  return `**${key}**: ${JSON.stringify(value, null, 2)}`;
                }
              }
              return `**${key}**: ${value}`;
            }).join('\n\n');
          } else {
            responseContent = 'Workflow executed successfully, but no output was generated.';
          }
        } else {
          responseContent = result.result || 'Workflow executed successfully.';
        }

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
    onExecute({ text: userInput, files: files.map(f => f.name) });
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-gray-200 flex items-center justify-between flex-shrink-0">
        <h2 className="text-lg font-semibold text-gray-900">Playground</h2>
        <button
          onClick={onClose}
          className="p-1 hover:bg-gray-100 rounded"
        >
          <X size={20} className="text-gray-500" />
        </button>
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
                      <div className="whitespace-pre-wrap">{message.content}</div>
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

        {/* File Upload Area */}
        {files.length > 0 && (
          <div className="p-4 border-t border-gray-200 flex-shrink-0">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Uploaded Files</h3>
            <div className="space-y-2">
              {files.map((file, index) => (
                <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                  <span className="text-sm text-gray-600 truncate">{file.name}</span>
                  <button
                    onClick={() => removeFile(index)}
                    className="text-red-500 hover:text-red-700"
                  >
                    <X size={16} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Input Area */}
        <div className="p-4 border-t border-gray-200 bg-white flex-shrink-0">
          <div className="flex items-center space-x-2 mb-3">
            <label className="flex items-center space-x-2 px-3 py-2 border border-gray-300 rounded-md cursor-pointer hover:bg-gray-50">
              <Upload size={16} className="text-gray-500" />
              <span className="text-sm text-gray-600">Upload Files</span>
              <input
                type="file"
                multiple
                className="hidden"
                onChange={handleFileUpload}
              />
            </label>
          </div>
          
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