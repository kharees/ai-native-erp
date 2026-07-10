'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import apiClient from '@/lib/apiClient';

interface Trend {
  date_label: string;
  total_sales: number;
  order_count: number;
}

interface SalesSummary {
  total_revenue: number;
  total_orders: number;
  average_order_value: number;
  trends: Trend[];
}

export default function SalesAnalyticsPage() {
  const [data, setData] = useState<SalesSummary | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    apiClient
      .get('/api/v1/omnichannel-billing/analytics/sales/trends', { params: { period: 'MTD' } })
      .then((res) => setData(res.data))
      .catch(() => setError('Failed to load sales analytics'));
  }, []);

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/omnichannel-billing/analytics/dashboard" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Billing Dashboard</Link>
          <h1 className="text-2xl font-bold">Sales Analytics</h1>
          <p className="text-gray-600 dark:text-gray-400">Sales trends for the current period.</p>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-medium text-gray-500">Total Revenue (MTD)</h3>
          <p className="text-3xl font-bold text-gray-900 dark:text-gray-100">{data ? `$${Number(data.total_revenue).toLocaleString()}` : '-'}</p>
        </div>
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-medium text-gray-500">Total Orders (MTD)</h3>
          <p className="text-3xl font-bold text-gray-900 dark:text-gray-100">{data ? data.total_orders : '-'}</p>
        </div>
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-medium text-gray-500">Avg. Order Value</h3>
          <p className="text-3xl font-bold text-gray-900 dark:text-gray-100">{data ? `$${Number(data.average_order_value).toFixed(2)}` : '-'}</p>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 border border-gray-200 dark:border-gray-700">
        <h3 className="font-bold mb-4">Sales Trend</h3>
        {!data ? (
          <p className="text-sm text-gray-500">Loading...</p>
        ) : data.trends.length === 0 ? (
          <p className="text-sm text-gray-500">No trend data available.</p>
        ) : (
          <ul className="space-y-2">
            {data.trends.map((t, idx) => (
              <li key={idx} className="flex justify-between text-sm p-2 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700">
                <span>{t.date_label}</span>
                <span>{t.order_count} orders</span>
                <span className="font-semibold">${Number(t.total_sales).toLocaleString()}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
