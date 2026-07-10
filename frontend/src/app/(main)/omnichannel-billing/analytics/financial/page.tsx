'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import apiClient from '@/lib/apiClient';

interface FinancialSummary {
  total_outstanding: number;
  total_collected: number;
  total_tax_collected: number;
  aging_buckets: Record<string, number>;
}

export default function FinancialAnalyticsPage() {
  const [data, setData] = useState<FinancialSummary | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    apiClient
      .get('/api/v1/omnichannel-billing/analytics/financial/summary')
      .then((res) => setData(res.data))
      .catch(() => setError('Failed to load financial analytics'));
  }, []);

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/omnichannel-billing/outstanding" className="text-blue-600 hover:underline text-sm mb-2 block">View Outstanding Dashboard &rarr;</Link>
          <h1 className="text-2xl font-bold">Financial Analytics</h1>
          <p className="text-gray-600 dark:text-gray-400">Track collections, outstanding agings, and tax summaries.</p>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700 border-t-4 border-t-red-500">
          <h3 className="text-sm font-medium text-gray-500">Total Outstanding</h3>
          <p className="text-3xl font-bold text-gray-900 dark:text-gray-100">{data ? `$${Number(data.total_outstanding).toLocaleString()}` : '-'}</p>
        </div>
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700 border-t-4 border-t-green-500">
          <h3 className="text-sm font-medium text-gray-500">Total Collected</h3>
          <p className="text-3xl font-bold text-gray-900 dark:text-gray-100">{data ? `$${Number(data.total_collected).toLocaleString()}` : '-'}</p>
        </div>
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700 border-t-4 border-t-blue-500">
          <h3 className="text-sm font-medium text-gray-500">Total Tax Collected</h3>
          <p className="text-3xl font-bold text-gray-900 dark:text-gray-100">{data ? `$${Number(data.total_tax_collected).toLocaleString()}` : '-'}</p>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 border border-gray-200 dark:border-gray-700">
        <h3 className="font-bold mb-4">Aging Buckets</h3>
        {data ? (
          <ul className="space-y-2">
            {Object.entries(data.aging_buckets).map(([bucket, amount]) => (
              <li key={bucket} className="flex justify-between text-sm p-2 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700">
                <span>{bucket.replace(/_/g, ' ')}</span>
                <span className="font-semibold">${Number(amount).toLocaleString()}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-500">Loading...</p>
        )}
      </div>
    </div>
  );
}
