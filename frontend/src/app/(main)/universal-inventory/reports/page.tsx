'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import apiClient from '@/lib/apiClient';

interface Summary {
  total_quantity: number;
  total_value: number;
  warehouse_count: number;
  item_count: number;
}

interface AgingItem {
  aging_bucket: string;
}

interface AbcItem {
  classification: string;
}

export default function ReportsDashboard() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [aging, setAging] = useState<AgingItem[]>([]);
  const [abc, setAbc] = useState<AbcItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([
      apiClient.get('/api/v1/universal-reports/summary'),
      apiClient.get('/api/v1/universal-reports/aging'),
      apiClient.get('/api/v1/universal-reports/abc-analysis'),
    ])
      .then(([summaryRes, agingRes, abcRes]) => {
        setSummary(summaryRes.data);
        setAging(Array.isArray(agingRes.data) ? agingRes.data : []);
        setAbc(Array.isArray(abcRes.data) ? abcRes.data : []);
      })
      .catch(() => setError('Failed to load inventory analytics'))
      .finally(() => setLoading(false));
  }, []);

  const deadStockPct = aging.length > 0 ? Math.round((aging.filter((a) => a.aging_bucket === '180+').length / aging.length) * 100) : 0;
  const bucketCounts = ['0-30', '31-90', '91-180', '180+'].map((bucket) => ({
    bucket,
    count: aging.filter((a) => a.aging_bucket === bucket).length,
  }));
  const abcCounts = ['A', 'B', 'C'].map((cls) => ({
    cls,
    count: abc.filter((a) => a.classification === cls).length,
  }));

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/universal-inventory" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Inventory Dashboard</Link>
          <h1 className="text-3xl font-bold">Executive Inventory Analytics</h1>
          <p className="text-gray-500 text-sm mt-1">Real-time valuation, aging, and KPI tracking.</p>
        </div>
        <div className="space-x-2">
          <Link href="/universal-inventory/reports/standard">
            <button className="bg-gray-200 text-gray-800 px-4 py-2 rounded shadow hover:bg-gray-300 transition-colors">Standard Reports (CSV)</button>
          </Link>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6 shadow">
          <h3 className="text-gray-500 dark:text-gray-400 font-semibold mb-2 text-sm uppercase tracking-wider">Total Inventory Value</h3>
          <p className="text-3xl font-bold text-gray-900 dark:text-white">{loading ? '-' : `$${Number(summary?.total_value || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`}</p>
        </div>
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6 shadow">
          <h3 className="text-gray-500 dark:text-gray-400 font-semibold mb-2 text-sm uppercase tracking-wider">Total Items on Hand</h3>
          <p className="text-3xl font-bold text-gray-900 dark:text-white">{loading ? '-' : Number(summary?.total_quantity || 0).toLocaleString()}</p>
        </div>
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6 shadow">
          <h3 className="text-gray-500 dark:text-gray-400 font-semibold mb-2 text-sm uppercase tracking-wider">Dead Stock (180+ Days)</h3>
          <p className="text-3xl font-bold text-red-600">{loading ? '-' : `${deadStockPct}%`}</p>
        </div>
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6 shadow">
          <h3 className="text-gray-500 dark:text-gray-400 font-semibold mb-2 text-sm uppercase tracking-wider">Warehouses</h3>
          <p className="text-3xl font-bold text-green-600">{loading ? '-' : summary?.warehouse_count ?? 0}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700">
          <h3 className="font-bold text-lg mb-4">ABC Analysis (Pareto Distribution)</h3>
          <ul className="space-y-2">
            {abcCounts.map(({ cls, count }) => (
              <li key={cls} className="flex justify-between p-3 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700">
                <span>Class {cls}</span>
                <span className="font-semibold">{count} item(s)</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700">
          <h3 className="font-bold text-lg mb-4">Inventory Aging Profile</h3>
          <ul className="space-y-2">
            {bucketCounts.map(({ bucket, count }) => (
              <li key={bucket} className="flex justify-between p-3 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700">
                <span>{bucket} days</span>
                <span className="font-semibold">{count} balance(s)</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
