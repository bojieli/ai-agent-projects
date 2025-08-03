import React from 'react';

interface TestCase {
  name: string;
  context: string;
  query: string;
}

interface TestCaseSelectorProps {
  testCases: TestCase[];
  selectedIndex: number;
  onSelect: (index: number) => void;
}

export default function TestCaseSelector({ testCases, selectedIndex, onSelect }: TestCaseSelectorProps) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4">
      <h3 className="text-lg font-semibold mb-3 text-gray-800 dark:text-white">选择测试用例</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
        {testCases.map((testCase, index) => (
          <button
            key={index}
            onClick={() => onSelect(index)}
            className={`
              p-4 rounded-lg border-2 transition-all duration-200 text-left
              ${selectedIndex === index
                ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
              }
            `}
          >
            <h4 className="font-medium text-sm text-gray-800 dark:text-white mb-1">
              {testCase.name}
            </h4>
            <p className="text-xs text-gray-600 dark:text-gray-400 line-clamp-2">
              {testCase.query}
            </p>
          </button>
        ))}
      </div>
    </div>
  );
}