'use client';

import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import TestCaseViewer from './TestCaseViewer';

interface ResultsViewerProps {
  markdown: string;
  json: Record<string, unknown>;
  jobId: string;
}

export default function ResultsViewer({ markdown, json, jobId }: ResultsViewerProps) {
  const [activeTab, setActiveTab] = useState<'markdown' | 'json' | 'testcases'>('testcases');

  const downloadMarkdown = () => {
    const blob = new Blob([markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `qa_documentation_${new Date().toISOString().slice(0, 10)}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const downloadJSON = () => {
    const blob = new Blob([JSON.stringify(json, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `qa_documentation_${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const downloadPDF = async () => {
    if (!jobId) {
      console.error("Job ID is not available, cannot download PDF.");
      return;
    }
    try {
      const response = await fetch(`/api/jobs/${jobId}/results/pdf`);
      if (!response.ok) {
        throw new Error(`Failed to download PDF: ${response.statusText}`);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `qa_documentation_${jobId}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Error downloading PDF:", error);
    }
  };

  return (
    <div className="w-full max-w-6xl mx-auto bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mt-8">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-medium text-gray-900 dark:text-white">Analysis Results</h3>
        
        <div className="flex space-x-2">
          <button
            onClick={downloadMarkdown}
            className="px-3 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 flex items-center"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Download Markdown
          </button>
          <button
            onClick={downloadJSON}
            className="px-3 py-2 bg-gray-600 hover:bg-gray-700 text-white text-sm font-medium rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 flex items-center"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Download JSON
          </button>
          <button
            onClick={downloadPDF}
            className="px-3 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-medium rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 flex items-center"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Download PDF
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="flex -mb-px">
          <button
            className={`py-2 px-4 text-sm font-medium ${
              activeTab === 'testcases'
                ? 'border-b-2 border-indigo-500 text-indigo-600 dark:text-indigo-400'
                : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
            }`}
            onClick={() => setActiveTab('testcases')}
          >
            Test Cases
          </button>
          <button
            className={`py-2 px-4 text-sm font-medium ${
              activeTab === 'markdown'
                ? 'border-b-2 border-indigo-500 text-indigo-600 dark:text-indigo-400'
                : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
            }`}
            onClick={() => setActiveTab('markdown')}
          >
            Markdown Source
          </button>
          <button
            className={`py-2 px-4 text-sm font-medium ${
              activeTab === 'json'
                ? 'border-b-2 border-indigo-500 text-indigo-600 dark:text-indigo-400'
                : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
            }`}
            onClick={() => setActiveTab('json')}
          >
            JSON Data
          </button>
        </nav>
      </div>

      {/* Tab content */}
      <div className="mt-6">
        {activeTab === 'testcases' ? (
          <TestCaseViewer markdown={markdown} />
        ) : activeTab === 'markdown' ? (
          <div className="prose prose-indigo dark:prose-invert max-w-none overflow-auto max-h-[600px] p-4 bg-gray-50 dark:bg-gray-900 rounded-md">
            <ReactMarkdown
              components={{
                code: ({ className, children, ...props}) => {
                  const match = /language-(\w+)/.exec(className || '');
                  return match ? (
                    <pre className="bg-gray-800 text-gray-100 p-4 rounded-md overflow-x-auto">
                      <code className={`language-${match[1]} text-sm`}>
                        {String(children).replace(/\n$/, '')}
                      </code>
                    </pre>
                  ) : (
                    <code className={className} {...props}>
                      {children}
                    </code>
                  );
                }
              }}
            >
              {markdown}
            </ReactMarkdown>
          </div>
        ) : (
          <div className="overflow-auto max-h-[600px] p-4 bg-gray-50 dark:bg-gray-900 rounded-md">
            <pre className="bg-gray-800 text-gray-100 p-4 rounded-md overflow-x-auto">
              <code className="language-json text-sm">
                {JSON.stringify(json, null, 2)}
              </code>
            </pre>
          </div>
        )}
      </div>
    </div>
  );
} 