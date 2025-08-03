import React from 'react';

interface VerdictDashboardProps {
  verificationResult: {
    sequence: string;
    tokens: string[];
    factuality_score: number;      // 核心指标：事实性得分
    avg_system_attention: number;  // 最大系统提示注意力（简化版）
    avg_user_attention: number;    // 平均用户提示注意力（不再使用）
    final_verdict: string;
    analyses: Array<{
      token: string;
      system_attention?: number;    // 对系统提示的注意力
      user_attention?: number;      // 对用户提示的注意力
      factuality_score?: number;    // 事实性得分
    }>;
    verdict_details: {
      max_system_attention?: number;
      threshold?: number;
      number_sequence_started?: boolean;
    };
  };
}

export default function VerdictDashboard({ verificationResult }: VerdictDashboardProps) {
  // 使用最大系统注意力（简化算法）
  const maxSystemAttention = (verificationResult.verdict_details.max_system_attention || verificationResult.avg_system_attention) * 100;
  const threshold = (verificationResult.verdict_details.threshold || 0.1) * 100;
  const factualityScore = verificationResult.factuality_score * 100;

  // 获取裁决的样式
  const getVerdictStyle = (verdict: string) => {
    switch (verdict) {
      case 'VERIFIED':
        return { color: '#10b981', bgColor: '#d1fae5', label: '✓ 已验证' };
      case 'SUSPICIOUS':
        return { color: '#f59e0b', bgColor: '#fef3c7', label: '⚠ 可疑' };
      case 'HALLUCINATION_DETECTED':
        return { color: '#ef4444', bgColor: '#fee2e2', label: '✗ 检测到幻觉' };
      default:
        return { color: '#6b7280', bgColor: '#f3f4f6', label: '未检测到序列' };
    }
  };

  const verdictStyle = getVerdictStyle(verificationResult.final_verdict);

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-6">验证分析仪表盘</h3>
      
      {/* 裁决结果 */}
      <div className="mb-8 p-6 rounded-lg" style={{ backgroundColor: verdictStyle.bgColor }}>
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-2xl font-bold" style={{ color: verdictStyle.color }}>
              {verdictStyle.label}
            </h4>
            <p className="text-gray-600 mt-2">序列: {verificationResult.sequence}</p>
          </div>
          <div className="text-right">
            <div className="text-4xl font-bold" style={{ color: verdictStyle.color }}>
              {factualityScore.toFixed(0)}%
            </div>
            <p className="text-sm text-gray-600">事实性得分</p>
          </div>
        </div>
      </div>

      {/* 简化的注意力分析 */}
      <div className="mb-8">
        <h4 className="text-md font-semibold mb-4">系统提示注意力检测</h4>
        {verificationResult.verdict_details.number_sequence_started && (
          <div className="bg-blue-50 p-3 rounded mb-4">
            <p className="text-sm">
              🔢 检测到数字序列开始
            </p>
          </div>
        )}
        <div className="bg-gray-50 p-4 rounded-lg mb-4">
          <div className="text-center">
            <div className="text-4xl font-bold mb-2" style={{ 
              color: maxSystemAttention > threshold ? '#10b981' : '#ef4444' 
            }}>
              {maxSystemAttention.toFixed(1)}%
            </div>
            <div className="text-sm text-gray-600 mb-4">最大系统提示注意力</div>
            <div className="flex items-center justify-center gap-2">
              <span className="text-sm text-gray-500">阈值:</span>
              <span className="text-sm font-semibold">{threshold.toFixed(0)}%</span>
            </div>
            {maxSystemAttention > threshold ? (
              <div className="mt-4 text-green-600 font-semibold">
                ✓ 高于阈值 - 非幻觉
              </div>
            ) : (
              <div className="mt-4 text-red-600 font-semibold">
                ✗ 低于阈值 - 检测到幻觉
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 详细说明 */}
      <div className="bg-gray-50 p-4 rounded-lg">
        <h4 className="text-sm font-semibold mb-2">简化算法说明</h4>
        <p className="text-sm text-gray-600">
          本系统使用简化的注意力峰值检测算法：
        </p>
        <ul className="text-sm text-gray-600 mt-2 space-y-1">
          <li>• <span className="font-semibold">检测时机</span>：当数字序列开始时（第一个包含数字的token）</li>
          <li>• <span className="font-semibold">检测方法</span>：计算系统提示部分（token 5 到系统提示结束）的最大注意力值</li>
          <li>• <span className="text-green-600 font-semibold">非幻觉</span>：最大注意力 &gt; {threshold.toFixed(0)}%</li>
          <li>• <span className="text-red-600 font-semibold">幻觉</span>：最大注意力 ≤ {threshold.toFixed(0)}%</li>
        </ul>
        <p className="text-xs text-gray-500 mt-3">
          注：忽略前5个token（通常有高注意力峰值），只分析对系统提示的注意力模式。
        </p>
      </div>
    </div>
  );
}