'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircleIcon, XCircleIcon, ArrowPathIcon } from '@heroicons/react/24/solid';

interface ScanStage {
  id: string;
  title: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  details?: string[];
  progress?: number;
}

interface PageScanInfo {
  url: string;
  title?: string;
  elementsFound: number;
  status: 'scanning' | 'completed' | 'failed';
  elements: Array<{
    type: string;
    selector: string;
    purpose?: string;
  }>;
}

interface ScanProgressUIProps {
  stages: ScanStage[];
  currentStage: string;
  scannedPages: PageScanInfo[];
  testCasesGenerated: number;
  totalTestCases?: number;
  onCancel?: () => void;
}

const ScanProgressUI: React.FC<ScanProgressUIProps> = ({
  stages,
  currentStage,
  scannedPages,
  testCasesGenerated,
  totalTestCases,
  onCancel
}) => {
  return (
    <div className="w-full max-w-4xl mx-auto p-6 space-y-8">
      {/* Overall Progress */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
        <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">
          Scan Progress
        </h2>
        
        {/* Stage Progress */}
        <div className="space-y-4">
          {stages.map((stage) => (
            <div key={stage.id} className="relative">
              <div className="flex items-center mb-2">
                <div className={`
                  w-8 h-8 rounded-full flex items-center justify-center
                  ${stage.status === 'completed' ? 'bg-green-100 dark:bg-green-900' :
                    stage.status === 'processing' ? 'bg-blue-100 dark:bg-blue-900' :
                    stage.status === 'failed' ? 'bg-red-100 dark:bg-red-900' :
                    'bg-gray-100 dark:bg-gray-700'}
                `}>
                  {stage.status === 'completed' && (
                    <CheckCircleIcon className="w-6 h-6 text-green-600 dark:text-green-400" />
                  )}
                  {stage.status === 'processing' && (
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                    >
                      <ArrowPathIcon className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                    </motion.div>
                  )}
                  {stage.status === 'failed' && (
                    <XCircleIcon className="w-6 h-6 text-red-600 dark:text-red-400" />
                  )}
                </div>
                <span className="ml-3 font-medium text-gray-900 dark:text-white">
                  {stage.title}
                </span>
              </div>
              
              {/* Progress bar */}
              {stage.progress !== undefined && (
                <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${stage.progress}%` }}
                    className="h-full bg-blue-600 dark:bg-blue-500"
                  />
                </div>
              )}
              
              {/* Stage details */}
              <AnimatePresence>
                {stage.status === 'processing' && stage.details && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="ml-11 mt-2 text-sm text-gray-600 dark:text-gray-400"
                  >
                    {stage.details.map((detail, index) => (
                      <div key={index} className="mb-1">{detail}</div>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ))}
        </div>
      </div>

      {/* Page Scanning Progress */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
        <h3 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">
          Pages Scanned
        </h3>
        <div className="space-y-4">
          {scannedPages.map((page, index) => (
            <motion.div
              key={page.url}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="border dark:border-gray-700 rounded-lg p-4"
            >
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-medium text-gray-900 dark:text-white">
                  {page.title || page.url}
                </h4>
                <span className={`
                  px-2 py-1 rounded-full text-sm
                  ${page.status === 'completed' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' :
                    page.status === 'scanning' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' :
                    'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'}
                `}>
                  {page.status}
                </span>
              </div>
              
              {/* Elements found */}
              <div className="mt-2">
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Elements found: {page.elementsFound}
                </p>
                <div className="mt-2 space-y-2">
                  {page.elements.map((element, idx) => (
                    <motion.div
                      key={idx}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="text-sm bg-gray-50 dark:bg-gray-900 p-2 rounded"
                    >
                      <span className="font-mono text-blue-600 dark:text-blue-400">
                        {element.type}
                      </span>
                      {element.purpose && (
                        <span className="ml-2 text-gray-600 dark:text-gray-400">
                          ({element.purpose})
                        </span>
                      )}
                    </motion.div>
                  ))}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Test Cases Progress */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
        <h3 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">
          Test Cases Generation
        </h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-gray-700 dark:text-gray-300">
              Generated: {testCasesGenerated}
              {totalTestCases && ` / ${totalTestCases}`}
            </span>
            {totalTestCases && (
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {Math.round((testCasesGenerated / totalTestCases) * 100)}%
              </span>
            )}
          </div>
          {totalTestCases && (
            <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${(testCasesGenerated / totalTestCases) * 100}%` }}
                className="h-full bg-green-600 dark:bg-green-500"
              />
            </div>
          )}
        </div>
      </div>

      {/* Cancel button */}
      {onCancel && (
        <div className="flex justify-center mt-6">
          <button
            onClick={onCancel}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            Cancel Scan
          </button>
        </div>
      )}
    </div>
  );
};

export default ScanProgressUI; 