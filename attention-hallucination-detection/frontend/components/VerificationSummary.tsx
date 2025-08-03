import React from 'react';

interface VerificationSummaryProps {
  testCase: {
    name: string;
    system_prompt?: string;
    user_prompt?: string;
    context?: string;
    query?: string;
  };
  generatedText: string;
  verificationResult: {
    sequence: string;
    final_verdict: string;
    is_hallucination: boolean;
    factuality_score: number;
  };
}

export default function VerificationSummary({ 
  testCase, 
  generatedText, 
  verificationResult 
}: VerificationSummaryProps) {
  const getVerdictColor = (verdict: string) => {
    switch (verdict) {
      case 'VERIFIED':
        return 'text-verified bg-green-100 dark:bg-green-900/20';
      case 'SUSPICIOUS':
        return 'text-suspicious bg-yellow-100 dark:bg-yellow-900/20';
      case 'HALLUCINATION_DETECTED':
        return 'text-hallucination bg-red-100 dark:bg-red-900/20';
      default:
        return 'text-gray-600 bg-gray-100 dark:bg-gray-900/20';
    }
  };

  const getVerdictEmoji = (verdict: string) => {
    switch (verdict) {
      case 'VERIFIED':
        return '✅';
      case 'SUSPICIOUS':
        return '⚠️';
      case 'HALLUCINATION_DETECTED':
        return '🚫';
      default:
        return '❓';
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 左侧：输入信息 */}
        <div>
          <h3 className="text-lg font-semibold mb-3 text-gray-800 dark:text-white">
            输入信息
          </h3>
          
          <div className="space-y-3">
            <div>
              <label className="text-sm font-medium text-gray-600 dark:text-gray-400">
                上下文：
              </label>
              <div className="mt-1 p-3 bg-gray-50 dark:bg-gray-900 rounded-md">
                <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                  {testCase.system_prompt || testCase.context || ''}
                </p>
              </div>
            </div>
            
            <div>
              <label className="text-sm font-medium text-gray-600 dark:text-gray-400">
                查询：
              </label>
              <div className="mt-1 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-md">
                <p className="text-sm text-gray-700 dark:text-gray-300">
                  {testCase.user_prompt || testCase.query || ''}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* 右侧：输出和判定 */}
        <div>
          <h3 className="text-lg font-semibold mb-3 text-gray-800 dark:text-white">
            生成结果与判定
          </h3>
          
          <div className="space-y-3">
            <div>
              <label className="text-sm font-medium text-gray-600 dark:text-gray-400">
                模型输出：
              </label>
              <div className="mt-1 p-3 bg-gray-50 dark:bg-gray-900 rounded-md">
                <p className="text-sm text-gray-700 dark:text-gray-300">
                  {generatedText}
                </p>
                {verificationResult.sequence && (
                  <p className="mt-2 text-xs text-gray-500 dark:text-gray-500">
                    检测序列：<code className="bg-gray-200 dark:bg-gray-700 px-1 rounded">
                      {verificationResult.sequence}
                    </code>
                  </p>
                )}
              </div>
            </div>
            
            <div>
              <label className="text-sm font-medium text-gray-600 dark:text-gray-400">
                最终裁决：
              </label>
              <div className={`
                mt-1 p-4 rounded-md flex items-center justify-between
                ${getVerdictColor(verificationResult.final_verdict)}
              `}>
                <div className="flex items-center space-x-2">
                  <span className="text-2xl">
                    {getVerdictEmoji(verificationResult.final_verdict)}
                  </span>
                  <span className="font-semibold">
                    {verificationResult.final_verdict.replace(/_/g, ' ')}
                  </span>
                </div>
                <div className="text-sm opacity-75">
                  事实性得分：{(verificationResult.factuality_score * 100).toFixed(1)}%
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}