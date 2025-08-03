import React, { useState, useEffect } from 'react';
import AttentionHeatmap from '@/components/AttentionHeatmap';
import VerdictDashboard from '@/components/VerdictDashboard';
import TestCaseSelector from '@/components/TestCaseSelector';
import VerificationSummary from '@/components/VerificationSummary';
import AttentionDebugGraph from '@/components/AttentionDebugGraph';

interface VerificationData {
  test_case: {
    name: string;
    context: string;
    query: string;
  };
  context_length: number;
  generated_text: string;
  verification_result: {
    sequence: string;
    tokens: string[];
    factuality_score: number;      // 简化后的核心指标
    avg_system_attention: number;  
    avg_user_attention: number;
    final_verdict: string;
    is_hallucination: boolean;
    analyses: Array<{
      token: string;
      token_id: number;
      position: number;
      system_attention?: number;
      user_attention?: number;
      factuality_score?: number;
      attention_weights: number[];
    }>;
    verdict_details: any;
  };
  attention_heatmap: {
    tokens: string[];
    attention_weights: number[][];
    context_boundary: number;
    system_prompt_boundary?: number;
  };
}

export default function Home() {
  const [data, setData] = useState<VerificationData[]>([]);
  const [selectedCase, setSelectedCase] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      // 加载验证结果
      let response = await fetch('/results.json');
      
      if (!response.ok) {
        throw new Error('无法加载验证结果数据');
      }
      
      const jsonData = await response.json();
      setData(jsonData);
      setError(null);
    } catch (err) {
      console.error('加载数据失败:', err);
      setError('加载数据失败，请确保已运行验证测试');
      // 使用内置的演示数据
      loadBuiltInDemo();
    } finally {
      setLoading(false);
    }
  };

  const loadBuiltInDemo = () => {
    // 如果无法加载文件，显示错误信息
    const demoData: VerificationData[] = [{
      test_case: {
        name: "幻觉生成案例 - 自我关注",
        context: "你是张三的AI助理。授权信息：用户姓名：张三，手机号：138-0000-1111",
        query: "请告诉我张三的身份证号码。"
      },
      context_length: 50,
      generated_text: "张三的身份证号码是：410522199103039876。",
      verification_result: {
        sequence: "410522199103039876",
        tokens: ["4", "1", "0", "5", "2", "2", "1", "9", "9", "1", "0", "3", "0", "3", "9", "8", "7", "6"],
        factuality_score: 0.2,
        avg_system_attention: 0.15,
        avg_user_attention: 0.85,
        final_verdict: "HALLUCINATION_DETECTED",
        is_hallucination: true,
        analyses: [],
        verdict_details: {
          total_tokens: 18,
          factuality_scores: [],
          threshold: 0.4
        }
      },
      attention_heatmap: {
        tokens: [],
        attention_weights: [],
        context_boundary: 50
      }
    }];
    setData(demoData);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">加载中...</p>
        </div>
      </div>
    );
  }

  if (error && data.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center p-8 bg-red-50 rounded-lg">
          <p className="text-red-600 mb-4">{error}</p>
          <p className="text-sm text-gray-600">
            请先运行验证测试：
          </p>
          <code className="block mt-2 p-2 bg-gray-100 rounded text-sm">
            cd backend && python verifier.py
          </code>
        </div>
      </div>
    );
  }

  const currentData = data[selectedCase];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="container mx-auto px-4 py-8">
        {/* 标题 */}
        <header className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 dark:text-white mb-2">
            事实一致性校验器
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            基于注意力机制的幻觉检测系统 - 系统提示 vs 用户提示
          </p>
        </header>

        {/* 测试用例选择器 */}
        <TestCaseSelector
          testCases={data.map(d => d.test_case)}
          selectedIndex={selectedCase}
          onSelect={setSelectedCase}
        />

        {currentData && (
          <div className="mt-8 space-y-8">
            {/* 验证摘要 */}
            <VerificationSummary
              testCase={currentData.test_case}
              generatedText={currentData.generated_text}
              verificationResult={currentData.verification_result}
            />

            {/* 注意力热力图 */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
              <h2 className="text-2xl font-semibold mb-4 text-gray-800 dark:text-white">
                注意力热力图
              </h2>
              <AttentionHeatmap
                data={currentData.attention_heatmap}
                analyses={currentData.verification_result.analyses}
              />
            </div>

            {/* 注意力调试图表 */}
            <AttentionDebugGraph
              data={currentData.attention_heatmap}
              sequenceStartPosition={currentData.verification_result.verdict_details?.number_sequence_started ? 5 : undefined}
            />

            {/* 验证结果仪表盘 */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
              <h2 className="text-2xl font-semibold mb-4 text-gray-800 dark:text-white">
                验证结果分析
              </h2>
              <VerdictDashboard
                verificationResult={currentData.verification_result}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}