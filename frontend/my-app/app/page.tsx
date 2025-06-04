'use client';

import { useState, useEffect } from 'react';
import Header from './components/Header';
import UrlForm from './components/UrlForm';
import ProgressTracker from './components/ProgressTracker';
import ResultsViewer from './components/ResultsViewer';

export default function Home() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<'pending' | 'processing' | 'completed' | 'failed'>('pending');
  const [isLoading, setIsLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [logs, setLogs] = useState<string[]>([]);
  const [results, setResults] = useState<{ markdown: string; json: any } | null>(null);
  const [error, setError] = useState<string | null>(null);

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
          setProgress(50);
          addLog('Processing website...');
        } else if (data.status === 'completed') {
          setProgress(100);
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
  }, [jobId, status]);

  const addLog = (message: string) => {
    setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${message}`]);
  };

  const handleSubmit = async (url: string, auth: any, context: any, userPrompt: string) => {
    setIsLoading(true);
    setJobId(null);
    setStatus('pending');
    setProgress(0);
    setLogs([]);
    setResults(null);
    setError(null);
    
    try {
      addLog(`Starting analysis of ${url}`);
      
      // Log request details for debugging
      console.log('Sending request to:', 'http://localhost:8000/jobs');
      console.log('Request body:', JSON.stringify({
        url,
        auth,
        website_context: context,
        user_prompt: userPrompt
      }));
      
      const response = await fetch('http://localhost:8000/jobs', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          url,
          auth,
          website_context: context,
          user_prompt: userPrompt
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
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Header />
      
      <main className="container mx-auto px-4 py-8">
        <UrlForm onSubmit={handleSubmit} isLoading={isLoading} />
        
        {jobId && (
          <ProgressTracker 
            status={status} 
            logs={logs} 
            progress={progress} 
          />
        )}
        
        {results && jobId && (
          <ResultsViewer 
            markdown={results.markdown} 
            json={results.json} 
            jobId={jobId}
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
      </main>
    </div>
  );
}
