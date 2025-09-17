import React, { useState } from 'react';
import { X, Play, Upload, MessageSquare } from 'lucide-react';

interface PlaygroundSidebarProps {
  onClose: () => void;
  onExecute: (inputData: Record<string, any>) => void;
}

const PlaygroundSidebar: React.FC<PlaygroundSidebarProps> = ({ onClose, onExecute }) => {
  const [inputText, setInputText] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [chatHistory, setChatHistory] = useState<Array<{ role: 'user' | 'assistant'; content: string }>>([]);

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const uploadedFiles = Array.from(event.target.files || []);
    setFiles(prev => [...prev, ...uploadedFiles]);
  };

  const handleExecute = () => {
    if (!inputText.trim()) return;

    const inputData = {
      text: inputText,
      files: files.map(f => f.name)
    };

    setChatHistory(prev => [
      ...prev,
      { role: 'user', content: inputText }
    ]);

    onExecute(inputData);
    setInputText('');
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="playground-sidebar">
      <div className="p-4 border-b border-gray-200 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Playground</h2>
        <button
          onClick={onClose}
          className="p-1 hover:bg-gray-100 rounded"
        >
          <X size={20} className="text-gray-500" />
        </button>
      </div>

      <div className="flex flex-col h-full">
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
                      : 'bg-gray-100 text-gray-900'
                  }`}
                >
                  {message.content}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* File Upload Area */}
        {files.length > 0 && (
          <div className="p-4 border-t border-gray-200">
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
        <div className="p-4 border-t border-gray-200 bg-white">
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
              disabled={!inputText.trim()}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center"
            >
              <Play size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PlaygroundSidebar;