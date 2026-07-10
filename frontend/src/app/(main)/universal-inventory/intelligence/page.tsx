'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import apiClient from '@/lib/apiClient';

interface Forecast {
  item_id: string;
  item_name: string;
  current_stock: number;
  projected_demand_30d: number;
  confidence_score: number;
  seasonality_trend: string;
}

interface Recommendation {
  item_id: string;
  item_name: string;
  recommendation_type: string;
  rationale: string;
  potential_savings: number;
}

interface Dashboard {
  health_score: number;
  total_alerts: number;
  optimization_opportunities: number;
  forecasts: Forecast[];
  recommendations: Recommendation[];
}

export default function AIDashboard() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    apiClient
      .get('/api/v1/universal-intelligence/dashboard')
      .then((res) => setDashboard(res.data))
      .catch(() => setError('Failed to load AI intelligence dashboard'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/universal-inventory" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Inventory Dashboard</Link>
          <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-purple-600 to-blue-600">AI Inventory Intelligence</h1>
          <p className="text-gray-500 text-sm mt-1">Predictive forecasting and actionable optimization recommendations.</p>
        </div>
        <div className="space-x-2">
          <Link href="/universal-inventory/intelligence/copilot">
            <button className="bg-purple-600 text-white px-4 py-2 rounded shadow hover:bg-purple-700 transition-colors flex items-center gap-2">
              <span>Ask AI Copilot</span>
            </button>
          </Link>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-gradient-to-br from-green-50 to-emerald-100 dark:from-green-900/20 dark:to-emerald-800/20 border border-green-200 dark:border-green-800 rounded-lg p-6 shadow-sm">
          <h3 className="text-green-800 dark:text-green-400 font-semibold mb-2">Inventory Health Score</h3>
          <div className="flex items-end gap-2">
            <p className="text-4xl font-bold text-green-700 dark:text-green-500">{loading ? '-' : dashboard?.health_score ?? 0}</p>
            <span className="text-green-600 mb-1">/ 100</span>
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6 shadow-sm">
          <h3 className="text-gray-500 dark:text-gray-400 font-semibold mb-2">Active AI Alerts</h3>
          <p className="text-3xl font-bold text-orange-600">{loading ? '-' : dashboard?.total_alerts ?? 0}</p>
        </div>
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6 shadow-sm">
          <h3 className="text-gray-500 dark:text-gray-400 font-semibold mb-2">Optimization Opportunities</h3>
          <p className="text-3xl font-bold text-blue-600">{loading ? '-' : dashboard?.optimization_opportunities ?? 0}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700 flex flex-col">
          <h3 className="font-bold text-lg mb-4 text-purple-700 dark:text-purple-400">Demand Forecasting</h3>
          <div className="flex-1 space-y-4">
            {loading ? (
              <p className="text-sm text-gray-500">Loading forecasts...</p>
            ) : !dashboard?.forecasts.length ? (
              <p className="text-sm text-gray-500">No forecasts available.</p>
            ) : dashboard.forecasts.map((f) => (
              <div key={f.item_id} className="border border-gray-100 dark:border-gray-700 rounded p-4">
                <div className="flex justify-between mb-2">
                  <span className="font-semibold">{f.item_name}</span>
                  <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">{Math.round(f.confidence_score * 100)}% Confidence</span>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Projected Demand (30d): <strong>{f.projected_demand_30d} Units</strong></p>
                <p className="text-sm text-gray-600 dark:text-gray-400">Trend: {f.seasonality_trend}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700 flex flex-col">
          <h3 className="font-bold text-lg mb-4 text-blue-700 dark:text-blue-400">Smart Optimizations</h3>
          <div className="flex-1 space-y-4">
            {loading ? (
              <p className="text-sm text-gray-500">Loading recommendations...</p>
            ) : !dashboard?.recommendations.length ? (
              <p className="text-sm text-gray-500">No recommendations available.</p>
            ) : dashboard.recommendations.map((r) => (
              <div key={r.item_id} className="border border-gray-100 dark:border-gray-700 rounded p-4">
                <div className="flex justify-between mb-2">
                  <span className="font-semibold">{r.item_name}</span>
                  <span className="text-xs bg-red-100 text-red-800 px-2 py-1 rounded">{r.recommendation_type}</span>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Rationale: {r.rationale}</p>
                <p className="text-sm text-green-600 font-semibold">Potential Savings: ${Number(r.potential_savings).toFixed(2)}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
