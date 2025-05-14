'use client';

import React, { useState } from 'react';

interface TestCase {
  id: string;
  originalId?: string;
  feature: string;
  title: string;
  type: string;
  priority: string;
  description: string;
  primaryElement?: {
    selector: string;
    purpose?: string;
  };
  steps?: {
    number: number;
    action: string;
    expectedResult: string;
  }[];
  preconditions?: string[];
  postconditions?: string[];
}

interface TestCaseViewerProps {
  markdown: string;
}

export default function TestCaseViewer({ markdown }: TestCaseViewerProps) {
  const [expandedTestCase, setExpandedTestCase] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<string>('all');
  const [filterPriority, setFilterPriority] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState<string>('');

  // Parse markdown to extract test cases
  const parseTestCases = (markdown: string): TestCase[] => {
    const testCases: TestCase[] = [];
    
    // Split the markdown by test case headers
    const testCaseSections = markdown.split(/###\s+Test\s+Case\s+ID:/i);
    
    // Skip the first element if it's empty or doesn't contain a test case
    for (let i = 1; i < testCaseSections.length; i++) {
      const section = testCaseSections[i].trim();
      
      // Extract test case ID
      const idMatch = section.match(/^(TC_[A-Z0-9_]+)/);
      const id = idMatch ? idMatch[1] : `Unknown-${i}`;
      
      // Add index to ensure uniqueness
      const uniqueId = `${id}-${i}`;
      
      // Extract feature tested - improved regex to be more flexible
      const featureMatch = section.match(/\*\*Feature(?:\s+Tested)?:\*\*\s*([\s\S]*?)(?=\n\*\*|\n$)/i);
      const feature = featureMatch ? featureMatch[1].trim() : '';
      
      // Extract title - improved regex
      const titleMatch = section.match(/\*\*Title:\*\*\s*([\s\S]*?)(?=\n\*\*|\n$)/i);
      const title = titleMatch ? titleMatch[1].trim() : '';
      
      // Extract type - improved regex
      const typeMatch = section.match(/\*\*Type:\*\*\s*([\s\S]*?)(?=\n\*\*|\n$)/i);
      const type = typeMatch ? typeMatch[1].trim() : '';
      
      // Extract priority - improved regex
      const priorityMatch = section.match(/\*\*Priority:\*\*\s*([\s\S]*?)(?=\n\*\*|\n$)/i);
      const priority = priorityMatch ? priorityMatch[1].trim() : '';
      
      // Extract description - improved to capture multi-line descriptions
      let description = '';
      const descriptionMatch = section.match(/\*\*Description:\*\*\s*([\s\S]*?)(?=\n\*\*|\n$|$)/i);
      if (descriptionMatch) {
        // Get the full description text and trim it
        description = descriptionMatch[1].trim();
      }
      
      // Extract primary element - improved regex with more flexible matching
      const primaryElementRegex = new RegExp("\\*\\*(?:Primary\\s+Element|Related\\s+Element|Element\\s+Under\\s+Test)(?:\\s+Under\\s+Test)?:\\*\\*\\s*([\s\S]*?)(?=\\n\\*\\*|\\n$|$)", "i");
      const primaryElementMatch = section.match(primaryElementRegex);
      let primaryElement;
      
      if (primaryElementMatch) {
        // Check for selector with backticks
        const selectorMatch = primaryElementMatch[1].match(/`([^`]+)`/);
        // Alternative format: just the selector without explanation
        const simpleSelectorMatch = !selectorMatch && primaryElementMatch[1].trim();
        
        const purposeMatch = primaryElementMatch[1].match(/Purpose:\s*(.*?)(?=\n|$)/i);
        
        if (selectorMatch || (simpleSelectorMatch && typeof simpleSelectorMatch === 'string')) {
          primaryElement = {
            selector: selectorMatch ? selectorMatch[1] : String(simpleSelectorMatch),
            purpose: purposeMatch ? purposeMatch[1].trim() : undefined
          };
        }
      }
      
      // Extract steps - improved regex for multi-line matching with better pattern recognition
      const stepsRegex = new RegExp("\\*\\*Steps:\\*\\*\\s*([\s\S]*?)(?=\\n\\*\\*|\\n$|$)", "i");
      const stepsMatch = section.match(stepsRegex);
      let steps = [];
      
      if (stepsMatch) {
        // Try to match numbered steps with action and expected result
        const stepPattern = /(\d+)\.?\s*\*\*Action:\*\*([\s\S]*?)\*\*Expected\s+Result:\*\*([\s\S]*?)(?=\n\s*\d+\.?\s*\*\*Action:\*\*|\n\*\*|\n$|$)/gi;
        let stepMatch;
        
        while ((stepMatch = stepPattern.exec(stepsMatch[1])) !== null) {
          steps.push({
            number: parseInt(stepMatch[1], 10),
            action: stepMatch[2].trim(),
            expectedResult: stepMatch[3].trim()
          });
        }
        
        // If no steps were found with the pattern above, try an alternative approach
        if (steps.length === 0) {
          // Look for numbered steps without the Action/Expected Result formatting
          const simpleStepPattern = /(\d+)\.?\s*([\s\S]*?)(?=\n\s*\d+\.|\n\*\*|\n$|$)/gi;
          while ((stepMatch = simpleStepPattern.exec(stepsMatch[1])) !== null) {
            // For simple steps, we just use the entire step as the action
            steps.push({
              number: parseInt(stepMatch[1], 10),
              action: stepMatch[2].trim(),
              expectedResult: "Not specified"
            });
          }
          
          // If still no steps, try splitting by lines with numbers
          if (steps.length === 0) {
            const stepLines = stepsMatch[1].split(/\n\s*\d+\.\s*/);
            
            for (let j = 1; j < stepLines.length; j++) {
              // Improved regex for multi-line matching
              const actionRegex = new RegExp("([\s\S]*?)(?=\\*\\*Expected\\s+Result:\\*\\*|$)", "i");
              const actionMatch = stepLines[j].match(actionRegex);
              
              const resultRegex = new RegExp("\\*\\*Expected\\s+Result:\\*\\*\\s*([\s\S]*?)(?=\\n\\s*\\d+\\.|\\n$|$)", "i");
              const resultMatch = stepLines[j].match(resultRegex);
              
              if (actionMatch) {
                steps.push({
                  number: j,
                  action: actionMatch[1].trim(),
                  expectedResult: resultMatch ? resultMatch[1].trim() : "Not specified"
                });
              }
            }
          }
        }
      }
      
      // Extract preconditions - improved regex for multi-line matching
      const preconditionsRegex = new RegExp("\\*\\*Preconditions:\\*\\*\\s*([\s\S]*?)(?=\\n\\*\\*|\\n$|$)", "i");
      const preconditionsMatch = section.match(preconditionsRegex);
      let preconditions: string[] = [];
      
      if (preconditionsMatch) {
        // First try to split by bullet points or numbers
        const preconditionItems = preconditionsMatch[1].split(/\n\s*[\*\-]\s*|\n\s*\d+\.\s*/);
        preconditions = preconditionItems
          .map(item => item.trim())
          .filter(item => item.length > 0);
          
        // If no items found, use the entire text as a single precondition
        if (preconditions.length === 0 && preconditionsMatch[1].trim()) {
          preconditions = [preconditionsMatch[1].trim()];
        }
      }
      
      // Extract postconditions - similar to preconditions
      const postconditionsRegex = new RegExp("\\*\\*Postconditions:\\*\\*\\s*([\s\S]*?)(?=\\n\\*\\*|\\n$|$)", "i");
      const postconditionsMatch = section.match(postconditionsRegex);
      let postconditions: string[] = [];
      
      if (postconditionsMatch) {
        // First try to split by bullet points or numbers
        const postconditionItems = postconditionsMatch[1].split(/\n\s*[\*\-]\s*|\n\s*\d+\.\s*/);
        postconditions = postconditionItems
          .map(item => item.trim())
          .filter(item => item.length > 0);
          
        // If no items found, use the entire text as a single postcondition
        if (postconditions.length === 0 && postconditionsMatch[1].trim()) {
          postconditions = [postconditionsMatch[1].trim()];
        }
      }
      
      // Fallback values for empty fields
      const finalTitle = title || `Test Case ${id}`;
      const finalType = type || 'Functional';
      const finalPriority = priority || 'Medium';
      const finalFeature = feature || 'General Functionality';
      
      testCases.push({
        id: uniqueId,
        originalId: id,
        feature: finalFeature,
        title: finalTitle,
        type: finalType,
        priority: finalPriority,
        description,
        primaryElement,
        steps,
        preconditions,
        postconditions
      });
    }
    
    return testCases;
  };

  const testCases = parseTestCases(markdown);
  
  // Filter test cases
  const filteredTestCases = testCases.filter(testCase => {
    const matchesType = filterType === 'all' || testCase.type.toLowerCase().includes(filterType.toLowerCase());
    const matchesPriority = filterPriority === 'all' || testCase.priority.toLowerCase().includes(filterPriority.toLowerCase());
    const matchesSearch = searchTerm === '' || 
      testCase.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      testCase.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
      testCase.feature.toLowerCase().includes(searchTerm.toLowerCase()) ||
      testCase.id.toLowerCase().includes(searchTerm.toLowerCase());
    
    return matchesType && matchesPriority && matchesSearch;
  });
  
  // Get unique types and priorities for filters
  const types = ['all', ...new Set(testCases.map(tc => tc.type.toLowerCase()))].filter(Boolean);
  const priorities = ['all', ...new Set(testCases.map(tc => tc.priority.toLowerCase()))].filter(Boolean);

  const toggleTestCase = (id: string) => {
    if (expandedTestCase === id) {
      setExpandedTestCase(null);
    } else {
      setExpandedTestCase(id);
    }
  };

  const getPriorityColor = (priority: string) => {
    const lowerPriority = priority.toLowerCase();
    if (lowerPriority.includes('high')) return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
    if (lowerPriority.includes('medium')) return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
    if (lowerPriority.includes('low')) return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
    return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200';
  };

  const getTypeColor = (type: string) => {
    const lowerType = type.toLowerCase();
    if (lowerType.includes('functional')) return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
    if (lowerType.includes('end-to-end')) return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200';
    if (lowerType.includes('usability')) return 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200';
    if (lowerType.includes('edge')) return 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200';
    return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200';
  };

  return (
    <div className="w-full max-w-6xl mx-auto bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 mt-8">
      <h2 className="text-2xl font-bold mb-6 text-gray-900 dark:text-white">Test Cases</h2>
      
      {/* Filters */}
      <div className="flex flex-col md:flex-row gap-4 mb-6">
        <div className="flex-1">
          <label htmlFor="search" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Search
          </label>
          <input
            type="text"
            id="search"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search test cases..."
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
          />
        </div>
        
        <div className="w-full md:w-1/4">
          <label htmlFor="type-filter" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Type
          </label>
          <select
            id="type-filter"
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
          >
            {types.map((type) => (
              <option key={type} value={type}>
                {type.charAt(0).toUpperCase() + type.slice(1)}
              </option>
            ))}
          </select>
        </div>
        
        <div className="w-full md:w-1/4">
          <label htmlFor="priority-filter" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Priority
          </label>
          <select
            id="priority-filter"
            value={filterPriority}
            onChange={(e) => setFilterPriority(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
          >
            {priorities.map((priority) => (
              <option key={priority} value={priority}>
                {priority.charAt(0).toUpperCase() + priority.slice(1)}
              </option>
            ))}
          </select>
        </div>
      </div>
      
      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-indigo-50 dark:bg-indigo-900/30 p-4 rounded-lg">
          <p className="text-sm text-gray-500 dark:text-gray-400">Total Test Cases</p>
          <p className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">{testCases.length}</p>
        </div>
        <div className="bg-blue-50 dark:bg-blue-900/30 p-4 rounded-lg">
          <p className="text-sm text-gray-500 dark:text-gray-400">Filtered Results</p>
          <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">{filteredTestCases.length}</p>
        </div>
        <div className="bg-green-50 dark:bg-green-900/30 p-4 rounded-lg">
          <p className="text-sm text-gray-500 dark:text-gray-400">High Priority</p>
          <p className="text-2xl font-bold text-green-600 dark:text-green-400">
            {testCases.filter(tc => tc.priority.toLowerCase().includes('high')).length}
          </p>
        </div>
        <div className="bg-purple-50 dark:bg-purple-900/30 p-4 rounded-lg">
          <p className="text-sm text-gray-500 dark:text-gray-400">End-to-End Tests</p>
          <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">
            {testCases.filter(tc => tc.type.toLowerCase().includes('end-to-end')).length}
          </p>
        </div>
      </div>
      
      {/* Test Cases List */}
      <div className="space-y-4">
        {filteredTestCases.length > 0 ? (
          filteredTestCases.map((testCase) => (
            <div 
              key={testCase.id}
              className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden transition-all duration-200"
            >
              {/* Test Case Header */}
              <div 
                onClick={() => toggleTestCase(testCase.id)}
                className="flex flex-col md:flex-row md:items-center justify-between p-4 cursor-pointer bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                <div className="flex-1">
                  <div className="flex items-center space-x-2 mb-2">
                    <span className="text-xs font-medium px-2.5 py-0.5 rounded-full bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300">
                      {testCase.originalId || testCase.id}
                    </span>
                    <span className={`text-xs font-medium px-2.5 py-0.5 rounded-full ${getPriorityColor(testCase.priority)}`}>
                      {testCase.priority || 'No Priority'}
                    </span>
                    <span className={`text-xs font-medium px-2.5 py-0.5 rounded-full ${getTypeColor(testCase.type)}`}>
                      {testCase.type || 'No Type'}
                    </span>
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{testCase.title || 'Untitled Test Case'}</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{testCase.feature || 'No Feature'}</p>
                </div>
                <div className="mt-2 md:mt-0">
                  <svg 
                    className={`w-6 h-6 text-gray-500 dark:text-gray-400 transform transition-transform ${expandedTestCase === testCase.id ? 'rotate-180' : ''}`}
                    fill="none" 
                    stroke="currentColor" 
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </div>
              
              {/* Test Case Details */}
              {expandedTestCase === testCase.id && (
                <div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
                  {/* Description */}
                  <div className="mb-4">
                    <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Description</h4>
                    <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-md">
                      <p className="text-gray-600 dark:text-gray-400 whitespace-pre-wrap">{testCase.description || 'No description provided.'}</p>
                    </div>
                  </div>
                  
                  {/* Preconditions */}
                  {testCase.preconditions && testCase.preconditions.length > 0 && (
                    <div className="mb-4">
                      <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Preconditions</h4>
                      <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-md">
                        <ul className="list-disc list-inside text-gray-600 dark:text-gray-400 pl-2">
                          {testCase.preconditions.map((precondition, index) => (
                            <li key={index} className="mb-1 whitespace-pre-wrap">{precondition}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )}
                  
                  {/* Primary Element */}
                  {testCase.primaryElement && (
                    <div className="mb-4">
                      <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Element Under Test</h4>
                      <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-md">
                        <p className="text-sm font-mono text-gray-600 dark:text-gray-400">
                          Selector: <span className="text-indigo-600 dark:text-indigo-400">{testCase.primaryElement.selector}</span>
                        </p>
                        {testCase.primaryElement.purpose && (
                          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1 whitespace-pre-wrap">
                            Purpose: {testCase.primaryElement.purpose}
                          </p>
                        )}
                      </div>
                    </div>
                  )}
                  
                  {/* Steps */}
                  {testCase.steps && testCase.steps.length > 0 && (
                    <div className="mb-4">
                      <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Steps</h4>
                      <div className="overflow-hidden bg-gray-50 dark:bg-gray-700 rounded-md">
                        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-600">
                          <thead className="bg-gray-100 dark:bg-gray-800">
                            <tr>
                              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider w-16">
                                #
                              </th>
                              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                Action
                              </th>
                              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                Expected Result
                              </th>
                            </tr>
                          </thead>
                          <tbody className="bg-gray-50 dark:bg-gray-700 divide-y divide-gray-200 dark:divide-gray-600">
                            {testCase.steps.map((step) => (
                              <tr key={step.number} className="hover:bg-gray-100 dark:hover:bg-gray-600">
                                <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                                  {step.number}
                                </td>
                                <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-300 whitespace-pre-wrap">
                                  {step.action}
                                </td>
                                <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-300 whitespace-pre-wrap">
                                  {step.expectedResult}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                  
                  {/* Postconditions */}
                  {testCase.postconditions && testCase.postconditions.length > 0 && (
                    <div className="mb-4">
                      <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Postconditions</h4>
                      <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-md">
                        <ul className="list-disc list-inside text-gray-600 dark:text-gray-400 pl-2">
                          {testCase.postconditions.map((postcondition, index) => (
                            <li key={index} className="mb-1 whitespace-pre-wrap">{postcondition}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )}

                  {/* Debug View (Hidden by Default) */}
                  <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
                    <button 
                      className="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 flex items-center"
                      onClick={(e) => {
                        e.stopPropagation();
                        const rawMarkdownElement = document.getElementById(`raw-markdown-${testCase.id}`);
                        if (rawMarkdownElement) {
                          rawMarkdownElement.classList.toggle('hidden');
                        }
                      }}
                    >
                      <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Debug: View Raw Markdown
                    </button>
                    <div id={`raw-markdown-${testCase.id}`} className="hidden mt-2 p-3 bg-gray-100 dark:bg-gray-900 rounded-md overflow-auto">
                      <pre className="text-xs text-gray-500 dark:text-gray-500 whitespace-pre-wrap font-mono">{`### Test Case ID: ${testCase.originalId || testCase.id}`}</pre>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))
        ) : (
          <div className="text-center py-10">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-white">No test cases found</h3>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Try adjusting your search or filter criteria.</p>
          </div>
        )}
      </div>
      
      {/* Pagination (simplified) */}
      {filteredTestCases.length > 10 && (
        <div className="flex justify-center mt-6">
          <nav className="inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">
            <a href="#" className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm font-medium text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-600">
              <span className="sr-only">Previous</span>
              <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fillRule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
            </a>
            <a href="#" className="relative inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600">
              1
            </a>
            <a href="#" className="relative inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 bg-indigo-50 dark:bg-indigo-900/30 text-sm font-medium text-indigo-600 dark:text-indigo-400 hover:bg-indigo-100 dark:hover:bg-indigo-800/30">
              2
            </a>
            <a href="#" className="relative inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600">
              3
            </a>
            <a href="#" className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm font-medium text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-600">
              <span className="sr-only">Next</span>
              <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
              </svg>
            </a>
          </nav>
        </div>
      )}
    </div>
  );
} 


