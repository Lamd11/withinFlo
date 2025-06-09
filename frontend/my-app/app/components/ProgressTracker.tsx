'use client';

import React, { useState } from 'react';
import { ChartBarIcon, CheckCircleIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';

interface JobProgress {
  total_elements: number;
  processed_elements: number;
  total_test_cases: number;
  generated_test_cases: number;
  current_phase: string;
  phase_progress: number;
  logs: string[];
}

interface ProgressTrackerProps {
  status: Status;
  progress: {
    current_phase: Status;
    phase_progress: number;
    logs: string[];
    processed_elements: number;
    total_elements: number;
    generated_test_cases: number;
  };
  logs: string[];
}

// Add type definitions at the top of the file
type Phase = 'queue' | 'crawling' | 'analysis' | 'complete';
type Status = 'pending' | 'crawling' | 'analyzing' | 'generating' | 'completed' | 'failed';

export default function ProgressTracker({ status, progress, logs }: ProgressTrackerProps) {
  const [showAdvanced, setShowAdvanced] = useState(false);

  const getStatusText = () => {
    switch (status) {
      case 'pending':
        return 'Waiting to start analysis...';
      case 'crawling':
        return 'Crawling website...';
      case 'analyzing':
        return `Analyzing elements (${progress.processed_elements}/${progress.total_elements})...`;
      case 'generating':
        return 'Generating documentation...';
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
      case 'crawling':
      case 'analyzing':
      case 'generating':
        return 'text-blue-600 dark:text-blue-400';
      case 'completed':
        return 'text-green-600 dark:text-green-400';
      case 'failed':
        return 'text-red-600 dark:text-red-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  const getProgressPercentage = () => {
    // Each phase represents 25% of the total progress (4 phases total)
    switch (status) {
      case 'pending':
        // Queue phase (0-25%)
        return 25; // When in queue, show progress up to queue completion
      case 'crawling':
        // Crawling phase (25-50%)
        return 25 + (progress.phase_progress * 0.25);
      case 'analyzing':
        // Analysis phase (50-75%)
        return 50 + (progress.phase_progress * 0.25);
      case 'generating':
        // Completion phase (75-100%)
        return 75 + (progress.phase_progress * 0.25);
      case 'completed':
        return 100;
      case 'failed':
        // Show progress up to the point of failure
        switch (progress.current_phase) {
          case 'pending':
            return Math.min(25, progress.phase_progress);
          case 'crawling':
            return Math.min(50, 25 + (progress.phase_progress * 0.25));
          case 'analyzing':
            return Math.min(75, 50 + (progress.phase_progress * 0.25));
          case 'generating':
            return Math.min(100, 75 + (progress.phase_progress * 0.25));
          default:
            return progress.phase_progress;
        }
      default:
        return 0;
    }
  };

  // Update the status steps section to better reflect progress
  const getStepStatus = (stepPhase: Phase) => {
    const phases: Record<Phase, Status[]> = {
      queue: ['pending'],
      crawling: ['crawling'],
      analysis: ['analyzing', 'generating'],
      complete: ['completed']
    };

    if (status === 'completed' && stepPhase === 'complete') {
      return 'complete';
    } else if (status === 'failed') {
      return phases[stepPhase].includes(progress.current_phase) ? 'current' : 
             getProgressPercentage() >= getPhaseStartPercentage(stepPhase) ? 'complete' : 'pending';
    } else if (phases[stepPhase].includes(status)) {
      return 'current';
    } else if (getProgressPercentage() >= getPhaseStartPercentage(stepPhase)) {
      return 'complete';
    }
    return 'pending';
  };

  const getPhaseStartPercentage = (phase: Phase) => {
    switch (phase) {
      case 'queue': return 0;
      case 'crawling': return 25;
      case 'analysis': return 50;
      case 'complete': return 75;
      default: return 0;
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

        {/* Progress Statistics */}
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-lg">
            <div className="text-sm text-gray-500 dark:text-gray-400">Elements</div>
            <div className="text-lg font-semibold text-gray-900 dark:text-white">
              {progress.processed_elements} / {progress.total_elements || '?'}
            </div>
          </div>
          <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-lg">
            <div className="text-sm text-gray-500 dark:text-gray-400">Test Cases</div>
            <div className="text-lg font-semibold text-gray-900 dark:text-white">
              {progress.generated_test_cases}
            </div>
          </div>
        </div>

        {/* Progress bar */}
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5 mb-4">
          <div 
            className={`h-2.5 rounded-full transition-all duration-300 ease-in-out ${
              status === 'failed' ? 'bg-red-600' : 'bg-indigo-600'
            }`}
            style={{ width: `${getProgressPercentage()}%` }}
          ></div>
        </div>

        {/* Status steps */}
        <div className="flex justify-between mb-6">
          {[
            { phase: 'queue', label: 'Queue' },
            { phase: 'crawling', label: 'Crawling' },
            { phase: 'analysis', label: 'Analysis' },
            { phase: 'complete', label: 'Complete' }
          ].map(({ phase, label }) => {
            const stepStatus = getStepStatus(phase as Phase);
            return (
              <div key={phase} className="flex flex-col items-center">
                <div className={`w-6 h-6 flex items-center justify-center rounded-full ${
                  stepStatus === 'complete' ? 'bg-indigo-600 text-white' :
                  stepStatus === 'current' ? 'bg-indigo-200 text-indigo-600 border-2 border-indigo-600' :
                  'bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
                }`}>
                  {stepStatus === 'complete' ? (
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"></path>
                    </svg>
                  ) : (
                    <span>{getPhaseStartPercentage(phase as Phase) / 25 + 1}</span>
                  )}
                </div>
                <span className="text-xs mt-1">{label}</span>
              </div>
            );
          })}
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
            {progress.logs.length > 0 ? (
              progress.logs.map((log, index) => (
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