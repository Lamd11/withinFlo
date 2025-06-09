'use client';

import { useState, useEffect } from 'react';
import Header from './components/Header';
import UrlForm from './components/UrlForm';
import ProgressTracker from './components/ProgressTracker';
import ResultsViewer from './components/ResultsViewer';

interface JobProgress {
  total_elements: number;
  processed_elements: number;
  total_test_cases: number;
  generated_test_cases: number;
  current_phase: string;
  phase_progress: number;
  logs: string[];
}

export default function Home() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<'pending' | 'crawling' | 'analyzing' | 'generating' | 'completed' | 'failed'>('pending');
  const [isLoading, setIsLoading] = useState(false);
  const [progress, setProgress] = useState<JobProgress>({
    total_elements: 0,
    processed_elements: 0,
    total_test_cases: 0,
    generated_test_cases: 0,
    current_phase: 'pending',
    phase_progress: 0,
    logs: []
  });
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
        if (data.progress) {
          setProgress(data.progress);
        }
        
        if (data.status === 'completed') {
          fetchResults();
        } else if (data.status === 'failed') {
          setError(data.error || 'Analysis failed');
        }
      } catch (error) {
        console.error('Error polling job status:', error);
        const errorMessage = `Error checking job status: ${error instanceof Error ? error.message : String(error)}`;
        setProgress(prev => ({
          ...prev,
          logs: [...prev.logs, errorMessage]
        }));
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [jobId, status]);

  const handleSubmit = async (url: string, auth: any = null, context: any = null) => {
    setIsLoading(true);
    setError(null);
    setProgress({
      total_elements: 0,
      processed_elements: 0,
      total_test_cases: 0,
      generated_test_cases: 0,
      current_phase: 'pending',
      phase_progress: 0,
      logs: []
    });
    setStatus('pending');

    try {
      const response = await fetch('http://localhost:8000/jobs', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url, auth, website_context: context }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setJobId(data.job_id);
    } catch (error) {
      console.error('Error submitting URL:', error);
      setError(error instanceof Error ? error.message : String(error));
    } finally {
      setIsLoading(false);
    }
  };

  const fetchResults = async () => {
    if (!jobId) return;

    try {
      const response = await fetch(`http://localhost:8000/jobs/${jobId}/results`);
      const data = await response.json();
      setResults(data);
    } catch (error) {
      console.error('Error fetching results:', error);
      setError(error instanceof Error ? error.message : String(error));
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900">
      <Header />
      
      <main className="container mx-auto px-4 py-8">
        <UrlForm onSubmit={handleSubmit} isLoading={isLoading} />
        
        {jobId && (
          <ProgressTracker 
            status={status} 
            progress={progress}
            logs={[]} // We're now using progress.logs instead
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
