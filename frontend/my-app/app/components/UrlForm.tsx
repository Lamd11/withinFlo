'use client';

import React, { useState, useRef, useEffect } from 'react';

interface UrlFormProps {
  onSubmit: (url: string, auth: any, context: any) => void;
  isLoading: boolean;
}

export default function UrlForm({ onSubmit, isLoading }: UrlFormProps) {
  const [url, setUrl] = useState('');
  const [urlError, setUrlError] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const formRef = useRef<HTMLFormElement>(null);
  
  // Auth state
  const [useAuth, setUseAuth] = useState(false);
  const [authType, setAuthType] = useState('basic');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [token, setToken] = useState('');
  const [tokenType, setTokenType] = useState('cookie');
  
  // Context state
  const [useContext, setUseContext] = useState(false);
  const [siteType, setSiteType] = useState('');
  const [pageDescription, setPageDescription] = useState('');
  const [userGoal, setUserGoal] = useState('');

  // Fix for handling clicks on show/hide advanced button
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      // Close advanced options if clicked outside
      if (formRef.current && !formRef.current.contains(event.target as Node)) {
        // Keep advanced open if it contains inputs with values
        const hasValues = 
          (useAuth && (username || password || token)) ||
          (useContext && (siteType || pageDescription || userGoal));
          
        if (!hasValues) {
          setShowAdvanced(false);
        }
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [useAuth, username, password, token, useContext, siteType, pageDescription, userGoal]);

  const validateUrl = (value: string) => {
    if (!value) {
      setUrlError('URL is required');
      return false;
    }
    
    try {
      new URL(value);
      setUrlError('');
      return true;
    } catch (e) {
      setUrlError('Please enter a valid URL (e.g., https://example.com)');
      return false;
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateUrl(url) || isLoading) return;
    
    // Prepare auth object
    let auth = null;
    if (useAuth) {
      if (authType === 'basic') {
        auth = { type: 'basic', username, password };
      } else if (authType === 'session') {
        auth = { type: 'session', token, token_type: tokenType };
      }
    }
    
    // Prepare context object
    let context = null;
    if (useContext) {
      context = {
        type: siteType,
        current_page_description: pageDescription,
        user_goal_on_page: userGoal
      };
    }
    
    onSubmit(url, auth, context);
  };

  const handleAnalyzeClick = () => {
    if (formRef.current) {
      // Manually trigger form submission when the button is clicked
      const submitEvent = new Event('submit', { cancelable: true, bubbles: true });
      formRef.current.dispatchEvent(submitEvent);
    }
  };

  const toggleAdvanced = (e: React.MouseEvent) => {
    e.preventDefault(); // Prevent any default behavior
    e.stopPropagation(); // Stop event propagation
    setShowAdvanced(!showAdvanced);
  };

  return (
    <div className="w-full max-w-2xl mx-auto bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
      <form ref={formRef} onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label htmlFor="url" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Website URL to Analyze
          </label>
          <div className="mt-1 relative rounded-md shadow-sm">
            <input
              type="text"
              id="url"
              name="url"
              value={url}
              onChange={(e) => {
                setUrl(e.target.value);
                if (urlError) validateUrl(e.target.value);
              }}
              placeholder="https://example.com"
              className={`block w-full px-4 py-3 rounded-md border ${
                urlError ? 'border-red-300 text-red-900' : 'border-gray-300 dark:border-gray-600'
              } focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white`}
              disabled={isLoading}
            />
            {urlError && (
              <div className="text-red-500 text-sm mt-1">{urlError}</div>
            )}
          </div>
        </div>

        <div className="flex items-center">
          <button
            type="button"
            onClick={toggleAdvanced}
            className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300 text-sm flex items-center"
          >
            {showAdvanced ? 'Hide' : 'Show'} Advanced Options
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

        {showAdvanced && (
          <div className="space-y-6 border-t border-gray-200 dark:border-gray-700 pt-4">
            {/* Authentication Options */}
            <div>
              <div className="flex items-center mb-4">
                <input
                  id="use-auth"
                  type="checkbox"
                  checked={useAuth}
                  onChange={() => setUseAuth(!useAuth)}
                  className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                />
                <label htmlFor="use-auth" className="ml-2 block text-sm text-gray-700 dark:text-gray-300">
                  Website requires authentication
                </label>
              </div>

              {useAuth && (
                <div className="ml-6 space-y-4">
                  <div className="flex space-x-4">
                    <div className="flex items-center">
                      <input
                        id="auth-basic"
                        name="auth-type"
                        type="radio"
                        value="basic"
                        checked={authType === 'basic'}
                        onChange={() => setAuthType('basic')}
                        className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300"
                      />
                      <label htmlFor="auth-basic" className="ml-2 block text-sm text-gray-700 dark:text-gray-300">
                        Basic Auth
                      </label>
                    </div>
                    <div className="flex items-center">
                      <input
                        id="auth-session"
                        name="auth-type"
                        type="radio"
                        value="session"
                        checked={authType === 'session'}
                        onChange={() => setAuthType('session')}
                        className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300"
                      />
                      <label htmlFor="auth-session" className="ml-2 block text-sm text-gray-700 dark:text-gray-300">
                        Session Token
                      </label>
                    </div>
                  </div>

                  {authType === 'basic' ? (
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label htmlFor="username" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          Username
                        </label>
                        <input
                          type="text"
                          id="username"
                          value={username}
                          onChange={(e) => setUsername(e.target.value)}
                          className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                        />
                      </div>
                      <div>
                        <label htmlFor="password" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          Password
                        </label>
                        <input
                          type="password"
                          id="password"
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                        />
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      <div>
                        <label htmlFor="token" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          Session Token
                        </label>
                        <input
                          type="text"
                          id="token"
                          value={token}
                          onChange={(e) => setToken(e.target.value)}
                          className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          Token Type
                        </label>
                        <div className="mt-1 flex space-x-4">
                          <div className="flex items-center">
                            <input
                              id="token-cookie"
                              name="token-type"
                              type="radio"
                              value="cookie"
                              checked={tokenType === 'cookie'}
                              onChange={() => setTokenType('cookie')}
                              className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300"
                            />
                            <label htmlFor="token-cookie" className="ml-2 block text-sm text-gray-700 dark:text-gray-300">
                              Cookie
                            </label>
                          </div>
                          <div className="flex items-center">
                            <input
                              id="token-bearer"
                              name="token-type"
                              type="radio"
                              value="bearer"
                              checked={tokenType === 'bearer'}
                              onChange={() => setTokenType('bearer')}
                              className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300"
                            />
                            <label htmlFor="token-bearer" className="ml-2 block text-sm text-gray-700 dark:text-gray-300">
                              Bearer
                            </label>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Website Context Options */}
            <div>
              <div className="flex items-center mb-4">
                <input
                  id="use-context"
                  type="checkbox"
                  checked={useContext}
                  onChange={() => setUseContext(!useContext)}
                  className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                />
                <label htmlFor="use-context" className="ml-2 block text-sm text-gray-700 dark:text-gray-300">
                  Provide additional context about the website
                </label>
              </div>

              {useContext && (
                <div className="ml-6 space-y-4">
                  <div>
                    <label htmlFor="site-type" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Website Type
                    </label>
                    <input
                      type="text"
                      id="site-type"
                      placeholder="E-commerce, Blog, SaaS Dashboard, etc."
                      value={siteType}
                      onChange={(e) => setSiteType(e.target.value)}
                      className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                    />
                  </div>
                  <div>
                    <label htmlFor="page-description" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Current Page Description
                    </label>
                    <input
                      type="text"
                      id="page-description"
                      placeholder="Product Detail Page, User Dashboard, etc."
                      value={pageDescription}
                      onChange={(e) => setPageDescription(e.target.value)}
                      className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                    />
                  </div>
                  <div>
                    <label htmlFor="user-goal" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Main User Goal on This Page
                    </label>
                    <input
                      type="text"
                      id="user-goal"
                      placeholder="Complete purchase, Find information, etc."
                      value={userGoal}
                      onChange={(e) => setUserGoal(e.target.value)}
                      className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        <div className="flex justify-end">
          <button
            type="button"
            onClick={handleAnalyzeClick}
            disabled={isLoading}
            className={`px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 ${
              isLoading ? 'opacity-70 cursor-not-allowed' : ''
            }`}
          >
            {isLoading ? (
              <div className="flex items-center">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Analyzing...
              </div>
            ) : (
              'Analyze Website'
            )}
          </button>
        </div>
      </form>
    </div>
  );
} 