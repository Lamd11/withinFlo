'use client';

import React, { useState } from 'react';

interface ProgressTrackerProps {
  status: 'pending' | 'processing' | 'completed' | 'failed';
  logs: string[];
  progress: number;
}

export default function ProgressTracker({ status, logs, progress }: ProgressTrackerProps) {
  const [showAdvanced, setShowAdvanced] = useState(false);

  const getStatusText = () => {
    switch (status) {
      case 'pending':
        return 'Waiting to start analysis...';
      case 'processing':
        return 'Analyzing website...';
      case 'completed':
        return 'Analysis completed successfully!';
      case 'failed':
        return 'Analysis failed. Please try again.';
      default:
        return 'Unknown status';
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'pending':
        return 'text-yellow-600 dark:text-yellow-400';
      case 'processing':
        return 'text-blue-600 dark:text-blue-400';
      case 'completed':
        return 'text-green-600 dark:text-green-400';
      case 'failed':
        return 'text-red-600 dark:text-red-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mt-8">
      <div className="flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">Analysis Progress</h3>
          <span className={`text-sm font-medium ${getStatusColor()}`}>
            {getStatusText()}
          </span>
        </div>

        {/* Progress bar */}
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5 mb-4">
          <div 
            className="bg-indigo-600 h-2.5 rounded-full transition-all duration-300 ease-in-out"
            style={{ width: `${progress}%` }}
          ></div>
        </div>

        {/* Status steps */}
        <div className="flex justify-between mb-6">
          <div className="flex flex-col items-center">
            <div className={`w-6 h-6 flex items-center justify-center rounded-full ${
              status !== 'pending' ? 'bg-indigo-600 text-white' : 'bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
            }`}>
              {status !== 'pending' ? (
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"></path>
                </svg>
              ) : (
                <span>1</span>
              )}
            </div>
            <span className="text-xs mt-1">Queue</span>
          </div>
          <div className="flex flex-col items-center">
            <div className={`w-6 h-6 flex items-center justify-center rounded-full ${
              status === 'processing' || status === 'completed' || status === 'failed' ? 'bg-indigo-600 text-white' : 'bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
            }`}>
              {status === 'completed' || status === 'failed' ? (
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"></path>
                </svg>
              ) : (
                <span>2</span>
              )}
            </div>
            <span className="text-xs mt-1">Crawling</span>
          </div>
          <div className="flex flex-col items-center">
            <div className={`w-6 h-6 flex items-center justify-center rounded-full ${
              status === 'completed' || status === 'failed' ? 'bg-indigo-600 text-white' : 'bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
            }`}>
              {status === 'completed' ? (
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"></path>
                </svg>
              ) : status === 'failed' ? (
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd"></path>
                </svg>
              ) : (
                <span>3</span>
              )}
            </div>
            <span className="text-xs mt-1">Analysis</span>
          </div>
          <div className="flex flex-col items-center">
            <div className={`w-6 h-6 flex items-center justify-center rounded-full ${
              status === 'completed' ? 'bg-green-600 text-white' : status === 'failed' ? 'bg-red-600 text-white' : 'bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
            }`}>
              {status === 'completed' ? (
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"></path>
                </svg>
              ) : status === 'failed' ? (
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd"></path>
                </svg>
              ) : (
                <span>4</span>
              )}
            </div>
            <span className="text-xs mt-1">Complete</span>
          </div>
        </div>

        {/* Advanced logs toggle */}
        <div className="flex items-center mt-2">
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300 text-sm flex items-center"
          >
            {showAdvanced ? 'Hide' : 'Show'} Advanced Logs
            <svg
              className={`ml-1 h-4 w-4 transform ${showAdvanced ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        </div>

        {/* Advanced logs */}
        {showAdvanced && (
          <div className="mt-4 bg-gray-100 dark:bg-gray-900 rounded-md p-3 max-h-60 overflow-y-auto font-mono text-xs">
            {logs.length > 0 ? (
              logs.map((log, index) => (
                <div key={index} className="py-1 border-b border-gray-200 dark:border-gray-800 last:border-0">
                  {log}
                </div>
              ))
            ) : (
              <div className="text-gray-500 dark:text-gray-400">No logs available yet.</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
} 