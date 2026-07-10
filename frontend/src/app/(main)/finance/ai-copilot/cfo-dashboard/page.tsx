'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import apiClient from '@/lib/apiClient';

interface Summary {
  revenue: number;
  netProfit: number;
  operatingMargin: number;
}

interface Insight {
  id: string;
  insight_type: string;
  title: string;
  description: string;
  severity: string;
}

export default function CFODashboardPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([
      apiClient.get('/api/v1/finance-reports/dashboard-summary'),
      apiClient.get('/api/v1/finance-ai/insights'),
    ])
      .then(([summaryRes, insightsRes]) => {
        setSummary(summaryRes.data);
        setInsights((insightsRes.data || []).slice(0, 5));
      })
      .catch(() => setError('Failed to load CFO dashboard'));
  }, []);

  if (error) return <div className="p-6 text-red-600">{error}</div>;
  if (!summary) return <div className="p-6">Loading dashboard...</div>;

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-6 border-b pb-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">AI CFO Dashboard</h1>
          <p className="text-gray-500">Executive Summary & Predictive Insights</p>
        </div>
        <div className="flex gap-2">
          <Link href="/finance/ai-copilot/chat">
            <button className="bg-indigo-600 text-white px-4 py-2 rounded shadow hover:bg-indigo-700">Ask Copilot</button>
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-white p-5 rounded-lg shadow-sm border border-gray-200">
          <p className="text-sm font-medium text-gray-500 mb-1">Revenue YTD</p>
          <p className="text-3xl font-bold text-gray-900">${Number(summary.revenue).toLocaleString()}</p>
        </div>
        <div className="bg-white p-5 rounded-lg shadow-sm border border-gray-200">
          <p className="text-sm font-medium text-gray-500 mb-1">Net Profit YTD</p>
          <p className="text-3xl font-bold text-gray-900">${Number(summary.netProfit).toLocaleString()}</p>
        </div>
        <div className="bg-white p-5 rounded-lg shadow-sm border border-gray-200">
          <p className="text-sm font-medium text-gray-500 mb-1">Operating Margin</p>
          <p className="text-3xl font-bold text-gray-900">{summary.operatingMargin}%</p>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
          <span className="text-indigo-600">💡</span> AI Recommendations
        </h2>
        <div className="space-y-4">
          {insights.length === 0 ? (
            <p className="text-sm text-gray-500">
              No AI insights recorded yet. Run a scan from the{' '}
              <Link href="/finance/ai-copilot/risk-dashboard" className="text-indigo-600 hover:underline">Risk Dashboard</Link>.
            </p>
          ) : insights.map((item) => (
            <div
              key={item.id}
              className={`p-4 rounded border ${item.severity === 'CRITICAL' || item.severity === 'HIGH' ? 'bg-orange-50 border-orange-100' : 'bg-indigo-50 border-indigo-100'}`}
            >
              <h3 className={`font-bold mb-1 ${item.severity === 'CRITICAL' || item.severity === 'HIGH' ? 'text-orange-900' : 'text-indigo-900'}`}>{item.title}</h3>
              <p className={`text-sm ${item.severity === 'CRITICAL' || item.severity === 'HIGH' ? 'text-orange-800' : 'text-indigo-800'}`}>{item.description}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
