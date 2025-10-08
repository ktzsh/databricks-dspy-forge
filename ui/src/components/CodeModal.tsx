import React, { useState, useEffect, useRef } from 'react';
import { X, Copy, Check, Download } from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface CodeModalProps {
  isOpen: boolean;
  onClose: () => void;
  code: string;
  workflowName: string;
}

const CodeModal: React.FC<CodeModalProps> = ({ isOpen, onClose, code, workflowName }) => {
  const [copied, setCopied] = useState(false);
  const modalRef = useRef<HTMLDivElement>(null);

  // Handle Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      // Focus the modal when it opens
      modalRef.current?.focus();
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy code:', err);
    }
  };

  const handleDownload = () => {
    const blob = new Blob([code], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${workflowName.replace(/\s+/g, '_')}_program.py`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    // Delay revocation to ensure download completes
    setTimeout(() => URL.revokeObjectURL(url), 100);
  };

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={handleBackdropClick}
      role="dialog"
      aria-modal="true"
      aria-labelledby="code-modal-title"
    >
      <div
        ref={modalRef}
        className="bg-white rounded-lg shadow-xl max-w-5xl w-full max-h-[90vh] flex flex-col"
        tabIndex={-1}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-200">
          <div>
            <h2 id="code-modal-title" className="text-2xl font-semibold text-slate-900">Generated DSPy Code</h2>
            <p className="text-sm text-slate-500 mt-1">{workflowName}</p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 transition-colors"
            aria-label="Close modal"
          >
            <X size={24} />
          </button>
        </div>

        {/* Code Content */}
        <div className="flex-1 overflow-auto p-6">
          <div className="rounded-lg overflow-hidden">
            <SyntaxHighlighter
              language="python"
              style={vscDarkPlus}
              customStyle={{
                margin: 0,
                borderRadius: '0.5rem',
                fontSize: '0.875rem',
                lineHeight: '1.5',
              }}
              showLineNumbers
            >
              {code}
            </SyntaxHighlighter>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-slate-200">
          <button
            onClick={handleDownload}
            className="flex items-center space-x-2 px-4 py-2 bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 transition-all duration-200 font-medium"
          >
            <Download size={16} />
            <span>Download</span>
          </button>
          <button
            onClick={handleCopy}
            className="flex items-center space-x-2 px-4 py-2 bg-brand-500 text-white rounded-lg hover:bg-brand-600 transition-all duration-200 font-medium"
          >
            {copied ? (
              <>
                <Check size={16} />
                <span>Copied!</span>
              </>
            ) : (
              <>
                <Copy size={16} />
                <span>Copy to Clipboard</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default CodeModal;
