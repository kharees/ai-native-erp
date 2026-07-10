'use client';

import { useEffect, useState, useCallback } from 'react';
import apiClient, { isApiError } from '@/lib/apiClient';

interface Insight {
  id: string;
  insight_type: string;
  title: string;
  description: string;
  severity: string;
  confidence_score: number;
  status: string;
}

export default function RiskDashboardPage() {
  const [insights, setInsights] = useState<Insight[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    apiClient
      .get('/api/v1/finance-ai/insights')
      .then((res) => setInsights(res.data || []))
      .catch(() => setError('Failed to load AI insights'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleScan = async () => {
    setScanning(true);
    setError('');
    try {
      await apiClient.post('/api/v1/finance-ai/scan-fraud');
      load();
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to run fraud scan');
    } finally {
      setScanning(false);
    }
  };

  const criticalCount = insights.filter((i) => i.severity === 'CRITICAL' && i.status === 'PENDING').length;
  const pendingCount = insights.filter((i) => i.status === 'PENDING').length;

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6 border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold">Fraud & Risk Dashboard</h1>
          <p className="text-gray-500 text-sm">Automated Anomaly Detection</p>
        </div>
        <button onClick={handleScan} disabled={scanning} className="bg-red-600 text-white px-4 py-2 rounded shadow hover:bg-red-700 font-medium disabled:opacity-50">
          {scanning ? 'Scanning...' : 'Run Deep Scan'}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <p className="text-gray-500 text-sm">Total Insights Logged</p>
          <p className="text-4xl font-bold text-green-600">{insights.length}</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <p className="text-gray-500 text-sm">Pending Critical Alerts</p>
          <p className="text-4xl font-bold text-red-600">{criticalCount}</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <p className="text-gray-500 text-sm">Pending Review</p>
          <p className="text-4xl font-bold text-orange-500">{pendingCount}</p>
        </div>
      </div>

      <h2 className="text-lg font-bold mb-4 text-gray-800">Actionable AI Insights</h2>
      <div className="space-y-4">
        {loading ? (
          <p className="text-sm text-gray-500">Loading insights...</p>
        ) : insights.length === 0 ? (
          <p className="text-sm text-gray-500">No insights recorded yet. Run a deep scan to generate some.</p>
        ) : insights.map((item) => (
          <div
            key={item.id}
            className="bg-white p-5 rounded-lg shadow-sm border-l-4 border-gray-200 flex flex-col md:flex-row justify-between items-start md:items-center"
            style={{ borderLeftColor: item.severity === 'CRITICAL' ? '#ef4444' : item.severity === 'HIGH' ? '#f97316' : '#3b82f6' }}
          >
            <div className="mb-4 md:mb-0">
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-xs font-bold px-2 py-1 rounded text-white ${item.severity === 'CRITICAL' ? 'bg-red-500' : item.severity === 'HIGH' ? 'bg-orange-500' : 'bg-blue-500'}`}>
                  {item.insight_type}
                </span>
                <h3 className="font-bold text-gray-900">{item.title}</h3>
                <span className="text-xs text-gray-400 bg-gray-100 px-2 rounded">Confidence: {Number(item.confidence_score)}%</span>
              </div>
              <p className="text-gray-600 text-sm mt-2">{item.description}</p>
            </div>

            <div className="flex gap-2 shrink-0">
              {item.status === 'PENDING' ? (
                <span className="text-sm font-bold text-orange-600 bg-orange-50 px-3 py-1 rounded border border-orange-200">Pending Review</span>
              ) : (
                <span className="text-sm font-bold text-green-600 bg-green-50 px-3 py-1 rounded border border-green-200">Resolved</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
