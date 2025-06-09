'use client';

import React, { useState } from 'react';
// Assuming react-markdown is used for content rendering as per previous advice
import ReactMarkdown from 'react-markdown'; 

// Example: Importing icons from Heroicons (solid variant)
import {
  InformationCircleIcon,
  ClipboardIcon,
  CubeIcon,
  TableCellsIcon,
  ClipboardDocumentCheckIcon,
  ChevronDownIcon,
  ChevronUpIcon, // For the expand/collapse icon
  MagnifyingGlassIcon, // For search
  TagIcon, // For Type
  ExclamationTriangleIcon, // For Priority High
  ShieldCheckIcon, // For Priority Medium
  CheckCircleIcon, // For Priority Low
  AdjustmentsHorizontalIcon, // For filters
  DocumentTextIcon, // For Raw Markdown toggle
  ChartBarIcon, // For Stats
  ArrowUpIcon,
  ArrowDownIcon,
  FunnelIcon,
  ViewColumnsIcon,
} from '@heroicons/react/24/solid'; // Or /24/outline

// Your TestCase interface (remains the same)
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

// Helper component for rendering markdown content consistently
const MarkdownRenderer = ({ content, inline = false, className = "" }: { content: string | undefined, inline?: boolean, className?: string }) => {
  if (!content) return null;
  
  // Using prose classes for nice defaults from @tailwindcss/typography
  const defaultClasses = "prose prose-sm dark:prose-invert max-w-none";
  
  if (inline) {
    return (
      <span className={className}>
        <ReactMarkdown>{content}</ReactMarkdown>
      </span>
    );
  }
  
  return (
    <div className={`${defaultClasses} ${className}`}>
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
};

type SortField = 'title' | 'priority' | 'type' | 'feature';
type SortDirection = 'asc' | 'desc';
type GroupBy = 'none' | 'feature' | 'type' | 'priority';

export default function TestCaseViewer({ markdown }: TestCaseViewerProps) {
  const [expandedTestCase, setExpandedTestCase] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<string>('all');
  const [filterPriority, setFilterPriority] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [showRawMarkdown, setShowRawMarkdown] = useState<Record<string, boolean>>({});
  const [currentPage, setCurrentPage] = useState<number>(1);
  const itemsPerPage = 10;
  const [sortField, setSortField] = useState<SortField>('title');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  const [groupBy, setGroupBy] = useState<GroupBy>('none');
  const [isFilterMenuOpen, setIsFilterMenuOpen] = useState(false);

  // Your parseTestCases function (assuming it's working correctly to extract raw values)
  const parseTestCases = (markdown: string): TestCase[] => {
    const testCases: TestCase[] = [];
    const testCaseSections = markdown.split(/###\s+Test\s+Case\s+ID:/i);
    for (let i = 1; i < testCaseSections.length; i++) {
      const section = "### Test Case ID:" + testCaseSections[i].trim(); 
      
      const idMatch = section.match(/###\s+Test\s+Case\s+ID:\s*(TC_[A-Z0-9_]+)/i);
      const id = idMatch ? idMatch[1] : `Unknown-${i}`;
      const uniqueId = `${id}-${i}`;
      
      const featureMatch = section.match(/\*\s*\*\*Feature(?:\s+Tested)?:\*\*\s*([\s\S]*?)(?=\n\*\s*\*\*|\n*$)/i);
      const feature = featureMatch ? featureMatch[1].trim() : '';
      
      const titleMatch = section.match(/\*\s*\*\*Title:\*\*\s*([\s\S]*?)(?=\n\*\s*\*\*|\n*$)/i);
      const title = titleMatch ? titleMatch[1].trim() : '';
      
      const typeMatch = section.match(/\*\s*\*\*Type:\*\*\s*([\s\S]*?)(?=\n\*\s*\*\*|\n*$)/i);
      const type = typeMatch ? typeMatch[1].trim() : '';
      
      const priorityMatch = section.match(/\*\s*\*\*Priority:\*\*\s*([\s\S]*?)(?=\n\*\s*\*\*|\n*$)/i);
      const priority = priorityMatch ? priorityMatch[1].trim() : 'Medium'; // Default if not found
      
      const descriptionMatch = section.match(/\*\s*\*\*Description:\*\*\s*([\s\S]*?)(?=\n\*\s*\*\*Primary Element|\n\*\s*\*\*Related Elements|\n\*\s*\*\*Preconditions|\n\*\s*\*\*Steps|\n\*\s*\*\*Postconditions|\n*$)/i);
      let description = descriptionMatch ? descriptionMatch[1].trim() : '';

      const primaryElementMatch = section.match(/\*\s*\*\*(?:Primary\s+Element\s+Under\s+Test|Element\s+Under\s+Test):\*\*\s*([\s\S]*?)(?=\n\*\s*\*\*|\n*$)/i);
      let primaryElement;
      if (primaryElementMatch) {
        const content = primaryElementMatch[1].trim();
        const selectorMatch = content.match(/Selector:\s*`([^`]+)`/i);
        const purposeMatch = content.match(/Purpose(?: in this test)?:\s*([\s\S]+)/i); // Made "in this test" optional
        primaryElement = {
          selector: selectorMatch ? selectorMatch[1].trim() : content.split('\n')[0].replace(/Selector:\s*/i, '').trim(),
          purpose: purposeMatch ? purposeMatch[1].trim() : undefined
        };
      }
      
      const preconditionsMatch = section.match(/\*\s*\*\*Preconditions:\*\*\s*([\s\S]*?)(?=\n\*\s*\*\*Steps|\n\*\s*\*\*|\n*$)/i);
      let preconditions: string[] = [];
      if (preconditionsMatch) {
        preconditions = preconditionsMatch[1].trim().split(/\n\s*[\*\-]\s*|\n\s*\d+\.\s*/)
                          .map(item => item.trim()).filter(item => item.length > 0);
        if (preconditions.length === 0 && preconditionsMatch[1].trim()) {
            preconditions = [preconditionsMatch[1].trim()];
        }
      }

      const stepsMatch = section.match(/\*\s*\*\*Steps:\*\*\s*([\s\S]*?)(?=\n\*\s*\*\*Postconditions|\n\*\s*\*\*|\n*$)/i);
      let steps = [];
      if (stepsMatch) {
        const stepPattern = /\d+\.\s*\*\*Action:\*\*\s*([\s\S]*?)\s*\*\*Expected\s+Result:\*\*\s*([\s\S]*?)(?=\n\s*\d+\.\s*\*\*Action|\n*$)/gi;
        let stepDetailMatch;
        let stepCounter = 1;
        while ((stepDetailMatch = stepPattern.exec(stepsMatch[1])) !== null) {
          steps.push({
            number: parseInt(stepDetailMatch[0].match(/^(\d+)/)?.[1] || (stepCounter++).toString(), 10),
            action: stepDetailMatch[1].trim(),
            expectedResult: stepDetailMatch[2].trim()
          });
        }
      }

      const postconditionsMatch = section.match(/\*\s*\*\*Postconditions:\*\*\s*([\s\S]*?)(?=\n\*\s*\*\*|\n*$)/i);
      let postconditions: string[] = [];
      if (postconditionsMatch) {
         postconditions = postconditionsMatch[1].trim().split(/\n\s*[\*\-]\s*|\n\s*\d+\.\s*/)
                           .map(item => item.trim()).filter(item => item.length > 0);
        if (postconditions.length === 0 && postconditionsMatch[1].trim()) {
            postconditions = [postconditionsMatch[1].trim()];
        }
      }
      
      testCases.push({
        id: uniqueId,
        originalId: id,
        feature: feature || 'General Functionality',
        title: title || `Test Case ${id}`,
        type: type || 'Functional',
        priority: priority, // Ensure this is just "High", "Medium", or "Low"
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
  
  // Sort function
  const sortTestCases = (a: TestCase, b: TestCase) => {
    const direction = sortDirection === 'asc' ? 1 : -1;
    switch (sortField) {
      case 'priority':
        const priorityOrder = { 'high': 0, 'medium': 1, 'low': 2 };
        return direction * (
          priorityOrder[a.priority.toLowerCase()] - priorityOrder[b.priority.toLowerCase()]
        );
      case 'title':
        return direction * a.title.localeCompare(b.title);
      case 'type':
        return direction * a.type.localeCompare(b.type);
      case 'feature':
        return direction * a.feature.localeCompare(b.feature);
      default:
        return 0;
    }
  };

  // Filter and sort test cases
  const filteredTestCases = testCases
    .filter(testCase => {
      const tcPriority = testCase.priority?.toLowerCase() || '';
      const tcType = testCase.type?.toLowerCase() || '';
      
      const matchesType = filterType === 'all' || tcType.includes(filterType.toLowerCase());
      const matchesPriority = filterPriority === 'all' || tcPriority.includes(filterPriority.toLowerCase());
      const matchesSearch = searchTerm === '' || 
        testCase.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        testCase.feature.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (testCase.description && testCase.description.toLowerCase().includes(searchTerm.toLowerCase()));
      
      return matchesType && matchesPriority && matchesSearch;
    })
    .sort(sortTestCases);

  // Group test cases if grouping is enabled
  const groupTestCases = (testCases: TestCase[]) => {
    if (groupBy === 'none') return { 'All Test Cases': testCases };
    
    return testCases.reduce((groups: { [key: string]: TestCase[] }, testCase) => {
      let groupKey = '';
      switch (groupBy) {
        case 'feature':
          groupKey = testCase.feature || 'Uncategorized';
          break;
        case 'type':
          groupKey = testCase.type || 'Uncategorized';
          break;
        case 'priority':
          groupKey = testCase.priority || 'Uncategorized';
          break;
      }
      if (!groups[groupKey]) groups[groupKey] = [];
      groups[groupKey].push(testCase);
      return groups;
    }, {});
  };

  const groupedTestCases = groupTestCases(filteredTestCases);
  
  // Pagination logic
  const pageCount = Math.ceil(filteredTestCases.length / itemsPerPage);
  const indexOfLastItem = currentPage * itemsPerPage;
  const indexOfFirstItem = indexOfLastItem - itemsPerPage;
  const currentItems = filteredTestCases.slice(indexOfFirstItem, indexOfLastItem);
  
  // Extract raw markdown for each test case
  const getTestCaseRawMarkdown = (id: string): string => {
    const testCase = testCases.find(tc => tc.id === id);
    if (!testCase?.originalId) return '';
    
    const testCaseSections = markdown.split(/###\s+Test\s+Case\s+ID:/i);
    for (let i = 1; i < testCaseSections.length; i++) {
      const section = testCaseSections[i].trim();
      if (section.startsWith(testCase.originalId)) {
        return `### Test Case ID:${section}`;
      }
    }
    return '';
  };
  
  const types = ['all', ...new Set(testCases.map(tc => tc.type?.toLowerCase() || '').filter(Boolean))];
  const priorities = ['all', ...new Set(testCases.map(tc => tc.priority?.toLowerCase() || '').filter(Boolean))];

  const toggleTestCase = (id: string) => {
    console.log(`Toggling test case with ID: ${id}, current expanded: ${expandedTestCase}`);
    setExpandedTestCase(expandedTestCase === id ? null : id);
  };

  const toggleRawMarkdown = (id: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent toggling the test case expansion
    setShowRawMarkdown(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  // Improved Priority Badges
  const PriorityBadge = ({ priorityValue }: { priorityValue: string }) => {
    const lowerPriority = priorityValue?.toLowerCase() || 'medium'; // Default to medium if undefined
    let colorClasses = 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-200';
    let Icon = ShieldCheckIcon; // Default icon

    if (lowerPriority.includes('high')) {
      colorClasses = 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200 border border-red-300 dark:border-red-700';
      Icon = ExclamationTriangleIcon;
    } else if (lowerPriority.includes('medium')) {
      colorClasses = 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-200 border border-yellow-300 dark:border-yellow-700';
      Icon = ShieldCheckIcon;
    } else if (lowerPriority.includes('low')) {
      colorClasses = 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-200 border border-green-300 dark:border-green-700';
      Icon = CheckCircleIcon;
    }

    return (
      <span className={`inline-flex items-center text-xs font-semibold px-2.5 py-1 rounded-full ${colorClasses}`}>
        <Icon className="w-3.5 h-3.5 mr-1.5" />
        {priorityValue || 'Medium'}
      </span>
    );
  };

  const TypeBadge = ({ typeValue }: { typeValue: string }) => {
    const lowerType = typeValue?.toLowerCase() || 'functional';
    let colorClasses = 'bg-gray-100 text-gray-700 dark:bg-gray-600 dark:text-gray-200';

    if (lowerType.includes('functional')) colorClasses = 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200 border border-blue-300 dark:border-blue-700';
    else if (lowerType.includes('end-to-end')) colorClasses = 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-200 border border-purple-300 dark:border-purple-700';
    else if (lowerType.includes('usability')) colorClasses = 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-200 border border-indigo-300 dark:border-indigo-700';
    else if (lowerType.includes('edge')) colorClasses = 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-200 border border-orange-300 dark:border-orange-700';
    
    return (
      <span className={`inline-flex items-center text-xs font-semibold px-2.5 py-1 rounded-full ${colorClasses}`}>
        <TagIcon className="w-3.5 h-3.5 mr-1.5" />
        {typeValue || 'Functional'}
      </span>
    );
  };

  // Section component for details
  const DetailSection = ({ title, icon: Icon, children }: { title: string, icon?: React.ElementType, children: React.ReactNode }) => (
    <div className="mb-6 p-4 border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm bg-white dark:bg-gray-800 hover:shadow-md transition-shadow">
      <h4 className="flex items-center text-md font-semibold text-gray-800 dark:text-gray-100 mb-2">
        {Icon && <Icon className="w-5 h-5 mr-2 text-indigo-500 dark:text-indigo-400" />}
        {title}
      </h4>
      <div className="text-gray-700 dark:text-gray-300">
        {children}
      </div>
    </div>
  );


  return (
    <div className="w-full max-w-6xl mx-auto bg-gray-50 dark:bg-gray-900 rounded-xl shadow-2xl p-6 sm:p-8 mt-8">
      <header className="mb-8">
        <h2 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white text-center">Test Case Dashboard</h2>
      </header>
      
      {/* Controls Bar */}
      <div className="sticky top-0 z-10 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 p-4 mb-4">
        <div className="flex flex-wrap gap-4 items-center justify-between">
          {/* Search */}
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <input
                type="text"
                placeholder="Search test cases..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 dark:bg-gray-800 dark:border-gray-700"
              />
              <MagnifyingGlassIcon className="absolute left-3 top-2.5 h-5 w-5 text-gray-400" />
            </div>
          </div>

          {/* Controls */}
          <div className="flex gap-2">
            {/* Sort Button */}
            <div className="relative">
              <button
                onClick={() => setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc')}
                className="px-3 py-2 border rounded-lg flex items-center gap-2 hover:bg-gray-50 dark:hover:bg-gray-800"
              >
                Sort by
                {sortDirection === 'asc' ? (
                  <ArrowUpIcon className="h-4 w-4" />
                ) : (
                  <ArrowDownIcon className="h-4 w-4" />
                )}
              </button>
              <select
                value={sortField}
                onChange={(e) => setSortField(e.target.value as SortField)}
                className="absolute inset-0 w-full opacity-0 cursor-pointer"
              >
                <option value="title">Title</option>
                <option value="priority">Priority</option>
                <option value="type">Type</option>
                <option value="feature">Feature</option>
              </select>
            </div>

            {/* Group By Button */}
            <div className="relative">
              <button className="px-3 py-2 border rounded-lg flex items-center gap-2 hover:bg-gray-50 dark:hover:bg-gray-800">
                <ViewColumnsIcon className="h-4 w-4" />
                Group by
              </button>
              <select
                value={groupBy}
                onChange={(e) => setGroupBy(e.target.value as GroupBy)}
                className="absolute inset-0 w-full opacity-0 cursor-pointer"
              >
                <option value="none">None</option>
                <option value="feature">Feature</option>
                <option value="type">Type</option>
                <option value="priority">Priority</option>
              </select>
            </div>

            {/* Filter Button */}
            <button
              onClick={() => setIsFilterMenuOpen(!isFilterMenuOpen)}
              className="px-3 py-2 border rounded-lg flex items-center gap-2 hover:bg-gray-50 dark:hover:bg-gray-800"
            >
              <FunnelIcon className="h-4 w-4" />
              Filters
            </button>
          </div>
        </div>

        {/* Filter Menu */}
        {isFilterMenuOpen && (
          <div className="mt-4 p-4 border rounded-lg bg-white dark:bg-gray-800">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Type</label>
                <select
                  value={filterType}
                  onChange={(e) => setFilterType(e.target.value)}
                  className="w-full p-2 border rounded-md dark:bg-gray-700"
                >
                  <option value="all">All Types</option>
                  {types.filter(t => t !== 'all').map(type => (
                    <option key={type} value={type}>{type}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Priority</label>
                <select
                  value={filterPriority}
                  onChange={(e) => setFilterPriority(e.target.value)}
                  className="w-full p-2 border rounded-md dark:bg-gray-700"
                >
                  <option value="all">All Priorities</option>
                  {priorities.filter(p => p !== 'all').map(priority => (
                    <option key={priority} value={priority}>{priority}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        )}
      </div>
      
      {/* Stats */}
      <div className="mb-8 grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-md">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-indigo-100 dark:bg-indigo-900/30 text-indigo-500 dark:text-indigo-400">
              <ChartBarIcon className="h-6 w-6" />
            </div>
            <div className="ml-4">
              <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Total Test Cases</h3>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">{testCases.length}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-md">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-green-100 dark:bg-green-900/30 text-green-500 dark:text-green-400">
              <CheckCircleIcon className="h-6 w-6" />
            </div>
            <div className="ml-4">
              <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Filtered Results</h3>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">{filteredTestCases.length}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-md">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-red-100 dark:bg-red-900/30 text-red-500 dark:text-red-400">
              <ExclamationTriangleIcon className="h-6 w-6" />
            </div>
            <div className="ml-4">
              <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">High Priority</h3>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                {testCases.filter(tc => tc.priority?.toLowerCase().includes('high')).length}
              </p>
            </div>
          </div>
        </div>
        
        <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-md">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-yellow-100 dark:bg-yellow-900/30 text-yellow-500 dark:text-yellow-400">
              <TagIcon className="h-6 w-6" />
            </div>
            <div className="ml-4">
              <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Types</h3>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">{types.length - 1}</p>
            </div>
          </div>
        </div>
      </div>
      
      {/* Test Cases List */}
      <div className="space-y-8">
        {Object.entries(groupedTestCases).map(([groupName, groupTestCases]) => (
          <div key={groupName} className="space-y-4">
            {groupBy !== 'none' && (
              <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
                {groupName}
              </h2>
            )}
            <div className="space-y-4">
              {groupTestCases.map((testCase) => (
                <div 
                  key={testCase.id}
                  className={`bg-white dark:bg-gray-800 rounded-lg shadow-lg hover:shadow-xl transition-shadow duration-300 ease-in-out overflow-hidden `}
                >
                  <div 
                    onClick={() => toggleTestCase(testCase.id)}
                    className="flex flex-col md:flex-row md:items-center justify-between p-4 sm:p-6 cursor-pointer border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                    role="button"
                    tabIndex={0}
                    aria-expanded={expandedTestCase === testCase.id}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        toggleTestCase(testCase.id);
                      }
                    }}
                  >
                    <div className="flex-1 mb-3 md:mb-0">
                      <div className="flex flex-wrap items-center gap-2 mb-2">
                        <span className="text-xs font-mono px-2.5 py-1 rounded-full bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-200">
                          {testCase.originalId || testCase.id}
                        </span>
                        <PriorityBadge priorityValue={testCase.priority} />
                        <TypeBadge typeValue={testCase.type} />
                      </div>
                      <h3 className="text-xl font-semibold text-indigo-600 dark:text-indigo-400">{testCase.title || 'Untitled Test Case'}</h3>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{testCase.feature || 'No Feature Specified'}</p>
                    </div>
                    <div className="flex-shrink-0">
                      {expandedTestCase === testCase.id ? (
                        <div 
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleTestCase(testCase.id);
                          }}
                          className="cursor-pointer"
                        >
                          <ChevronUpIcon className="w-8 h-8 text-indigo-600 dark:text-indigo-400 p-1 bg-indigo-50 dark:bg-indigo-900/30 rounded-full" />
                        </div>
                      ) : (
                        <div 
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleTestCase(testCase.id);
                          }}
                          className="cursor-pointer"
                        >
                          <ChevronDownIcon className="w-8 h-8 text-gray-600 dark:text-gray-400 p-1 bg-gray-50 dark:bg-gray-700/50 rounded-full hover:bg-gray-100 dark:hover:bg-gray-600/50" />
                        </div>
                      )}
                    </div>
                  </div>
                  
                  {expandedTestCase === testCase.id && (
                    <div className="p-4 sm:p-6 bg-gray-50 dark:bg-gray-800/50 animate-fadeIn">
                      
                      <DetailSection title="Description" icon={InformationCircleIcon}>
                        <MarkdownRenderer content={testCase.description || 'No description provided.'} className="text-gray-700 dark:text-gray-300" />
                      </DetailSection>
                      
                      {testCase.preconditions && testCase.preconditions.length > 0 && (
                        <DetailSection title="Preconditions" icon={ClipboardIcon}>
                          <ul className="space-y-1">
                            {testCase.preconditions.map((precondition, index) => (
                              <li key={index} className="flex items-start">
                                <CheckCircleIcon className="w-4 h-4 mr-2 mt-1 flex-shrink-0 text-green-500 dark:text-green-400" />
                                <MarkdownRenderer content={precondition} inline={true} className="text-gray-700 dark:text-gray-300"/>
                              </li>
                            ))}
                          </ul>
                        </DetailSection>
                      )}
                      
                      {testCase.primaryElement && (
                        <DetailSection title="Element Under Test" icon={CubeIcon}>
                          <div className="p-3 bg-indigo-50 dark:bg-indigo-900/30 rounded-md border border-indigo-200 dark:border-indigo-700">
                            <p className="text-sm font-mono text-indigo-700 dark:text-indigo-300 break-all">
                              <strong>Selector:</strong> {testCase.primaryElement.selector}
                            </p>
                            {testCase.primaryElement.purpose && (
                              <div className="mt-2 text-sm text-indigo-600 dark:text-indigo-400">
                                 <strong>Purpose:</strong> <MarkdownRenderer content={testCase.primaryElement.purpose} inline={true} />
                              </div>
                            )}
                          </div>
                        </DetailSection>
                      )}
                      
                      {testCase.steps && testCase.steps.length > 0 && (
                        <DetailSection title="Steps" icon={TableCellsIcon}>
                          <div className="overflow-x-auto border border-gray-200 dark:border-gray-700 rounded-md">
                            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                              <thead className="bg-gray-100 dark:bg-gray-700/50">
                                <tr>
                                  <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider w-12 sm:w-16">#</th>
                                  <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Action</th>
                                  <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Expected Result</th>
                                </tr>
                              </thead>
                              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                                {testCase.steps.map((step, index) => (
                                  <tr key={step.number} className={index % 2 === 0 ? 'bg-white dark:bg-gray-800' : 'bg-gray-50 dark:bg-gray-800/60 hover:bg-gray-100 dark:hover:bg-gray-700/70'}>
                                    <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-700 dark:text-gray-200 text-center">{step.number}</td>
                                    <td className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300"><MarkdownRenderer content={step.action} /></td>
                                    <td className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300"><MarkdownRenderer content={step.expectedResult} /></td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </DetailSection>
                      )}
                      
                      {testCase.postconditions && testCase.postconditions.length > 0 && (
                         <DetailSection title="Postconditions" icon={ClipboardDocumentCheckIcon}>
                          <ul className="space-y-1">
                            {testCase.postconditions.map((postcondition, index) => (
                              <li key={index} className="flex items-start">
                                <ShieldCheckIcon className="w-4 h-4 mr-2 mt-1 flex-shrink-0 text-blue-500 dark:text-blue-400" />
                                <MarkdownRenderer content={postcondition} inline={true} className="text-gray-700 dark:text-gray-300"/>
                              </li>
                            ))}
                          </ul>
                        </DetailSection>
                      )}

                      {/* Raw Markdown Debug View */}
                      <div className="mt-8 pt-4 border-t border-gray-300 dark:border-gray-700">
                        <button 
                          className="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 flex items-center font-medium group"
                          onClick={(e) => toggleRawMarkdown(testCase.id, e)}
                        >
                          <DocumentTextIcon className="w-4 h-4 mr-1.5 text-gray-400 dark:text-gray-500 group-hover:text-gray-600 dark:group-hover:text-gray-300" />
                          Toggle Raw Markdown View
                        </button>
                        {showRawMarkdown[testCase.id] && (
                          <pre className="mt-2 p-3 bg-gray-100 dark:bg-gray-800 rounded-md overflow-x-auto text-xs font-mono text-gray-800 dark:text-gray-200">
                            {getTestCaseRawMarkdown(testCase.id)}
                          </pre>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
      
      {/* Pagination */}
      {filteredTestCases.length > itemsPerPage && (
        <div className="flex justify-center mt-6">
          <nav className="inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">
            <button
              onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
              disabled={currentPage === 1}
              className={`relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm font-medium ${
                currentPage === 1 
                  ? 'text-gray-300 dark:text-gray-600 cursor-not-allowed' 
                  : 'text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-600'
              }`}
            >
              <span className="sr-only">Previous</span>
              <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fillRule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
            </button>
            
            {Array.from({ length: pageCount }, (_, i) => i + 1).map(page => (
              <button
                key={page}
                onClick={() => setCurrentPage(page)}
                className={`relative inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium ${
                  currentPage === page
                    ? 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400'
                    : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600'
                }`}
              >
                {page}
              </button>
            ))}
            
            <button
              onClick={() => setCurrentPage(prev => Math.min(prev + 1, pageCount))}
              disabled={currentPage === pageCount}
              className={`relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm font-medium ${
                currentPage === pageCount 
                  ? 'text-gray-300 dark:text-gray-600 cursor-not-allowed' 
                  : 'text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-600'
              }`}
            >
              <span className="sr-only">Next</span>
              <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
              </svg>
            </button>
          </nav>
        </div>
      )}
    </div>
  );
}