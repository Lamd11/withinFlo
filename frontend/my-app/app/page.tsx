'use client';

import { useState, useEffect } from 'react';
import Header from './components/Header';
import ProgressTracker from './components/ProgressTracker';
import ResultsViewer from './components/ResultsViewer';
import LandingPage from './components/LandingPage';

export default function Home() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<'pending' | 'processing' | 'completed' | 'failed'>('pending');
  const [isLoading, setIsLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [logs, setLogs] = useState<string[]>([]);
  const [results, setResults] = useState<{ markdown: string; json: any } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elementCount, setElementCount] = useState<number>(0);
  const [processedElements, setProcessedElements] = useState<number>(0);

  // Poll for job status
  useEffect(() => {
    if (!jobId || status === 'completed' || status === 'failed') return;

    const interval = setInterval(async () => {
      try {
        const response = await fetch(`http://localhost:8000/jobs/${jobId}/status`);
        const data = await response.json();
        
        setStatus(data.status);
        
        // Update progress based on status
        if (data.status === 'pending') {
          setProgress(10);
          addLog('Job queued, waiting to start...');
        } else if (data.status === 'processing') {
          // Simulate progress for elements being processed
          if (data.progress) {
            // If the backend provides progress information
            setElementCount(data.total_elements || 100);
            setProcessedElements(data.processed_elements || 0);
            setProgress(Math.min(10 + (data.processed_elements / data.total_elements * 80), 90));
          } else {
            // If no detailed progress, just simulate
            const simulatedProgress = Math.min(progress + 5, 90);
            setProgress(simulatedProgress);
            
            // Simulate element counting
            if (elementCount === 0) {
              setElementCount(Math.floor(Math.random() * 30) + 20); // Random number between 20-50
            }
            
            setProcessedElements(Math.min(
              Math.floor((simulatedProgress - 10) / 80 * elementCount), 
              elementCount
            ));
          }
          
          addLog(`Processing website... ${processedElements}/${elementCount} elements analyzed`);
        } else if (data.status === 'completed') {
          setProgress(100);
          setProcessedElements(elementCount);
          addLog('Analysis completed successfully!');
          fetchResults();
        } else if (data.status === 'failed') {
          setProgress(100);
          setError(data.error || 'Analysis failed');
          addLog(`Error: ${data.error || 'Unknown error'}`);
        }
      } catch (error) {
        console.error('Error polling job status:', error);
        addLog(`Error checking job status: ${error instanceof Error ? error.message : String(error)}`);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [jobId, status, progress, elementCount, processedElements]);

  const addLog = (message: string) => {
    setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${message}`]);
  };

  const handleSubmit = async (url: string, auth: any, context: any) => {
    setIsLoading(true);
    setJobId(null);
    setStatus('pending');
    setProgress(0);
    setLogs([]);
    setResults(null);
    setError(null);
    setElementCount(0);
    setProcessedElements(0);
    
    try {
      addLog(`Starting analysis of ${url}`);
      
      // Log request details for debugging
      console.log('Sending request to:', 'http://localhost:8000/jobs');
      console.log('Request body:', JSON.stringify({
        url,
        auth,
        website_context: context
      }));
      
      const response = await fetch('http://localhost:8000/jobs', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          url,
          auth,
          website_context: context
        }),
      });
      
      // Log response status for debugging
      console.log('Response status:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Error response:', errorText);
        throw new Error(`Server responded with ${response.status}: ${errorText || response.statusText}`);
      }
      
      const data = await response.json();
      console.log('Response data:', data);
      setJobId(data.job_id);
      addLog(`Job created with ID: ${data.job_id}`);
    } catch (error) {
      console.error('Error submitting job:', error);
      setStatus('failed');
      setError(error instanceof Error ? error.message : 'Failed to submit job');
      addLog(`Error: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchResults = async () => {
    if (!jobId) return;
    
    try {
      const response = await fetch(`http://localhost:8000/jobs/${jobId}/results`);
      
      if (!response.ok) {
        throw new Error(`Server responded with ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      setResults({
        markdown: data.markdown || '# No test cases generated',
        json: data.json || {}
      });
      addLog('Results fetched successfully');
    } catch (error) {
      console.error('Error fetching results:', error);
      setError(error instanceof Error ? error.message : 'Failed to fetch results');
      addLog(`Error fetching results: ${error instanceof Error ? error.message : String(error)}`);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white dark:from-gray-900 dark:to-gray-800">
      {/* Always show the landing page */}
      <LandingPage onSubmit={handleSubmit} isLoading={isLoading} />
      
      {/* Show job processing and results below the landing page if a job has been submitted */}
      {(jobId || results || error) && (
        <div className="container mx-auto px-4 py-8 mt-8">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl p-6">
            <h2 className="text-2xl font-bold mb-6 text-gray-800 dark:text-white">Analysis Results</h2>
            
            {jobId && status !== 'completed' && (
              <ProgressTracker 
                status={status} 
                logs={logs} 
                progress={progress}
                elementCount={elementCount}
                processedElements={processedElements}
              />
            )}
            
            {results && (
              <ResultsViewer 
                markdown={results.markdown} 
                json={results.json} 
              />
            )}
            
            {error && (
              <div className="w-full max-w-2xl mx-auto bg-red-50 dark:bg-red-900 border-l-4 border-red-500 p-4 mt-8 rounded-md">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <p className="text-sm text-red-700 dark:text-red-200">
                      {error}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
