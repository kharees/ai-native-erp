'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import apiClient from '@/lib/apiClient';

interface LeaderboardItem {
  name: string;
  value: number;
  count: number;
}

interface Leaderboards {
  top_products: LeaderboardItem[];
  top_customers: LeaderboardItem[];
  top_channels: LeaderboardItem[];
}

export default function AnalyticsDashboardPage() {
  const [data, setData] = useState<Leaderboards | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    apiClient
      .get('/api/v1/omnichannel-billing/analytics/sales/leaderboards')
      .then((res) => setData(res.data))
      .catch(() => setError('Failed to load executive dashboard'));
  }, []);

  const renderList = (title: string, items: LeaderboardItem[]) => (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700">
      <div className="p-4 border-b">
        <h2 className="font-bold">{title}</h2>
      </div>
      {items.length === 0 ? (
        <div className="p-4 text-center text-sm text-gray-500">No data available.</div>
      ) : (
        <ul className="divide-y divide-gray-100 dark:divide-gray-700">
          {items.map((item, idx) => (
            <li key={idx} className="p-4 flex justify-between text-sm">
              <span>{item.name}</span>
              <span className="font-semibold">${Number(item.value).toLocaleString()} ({item.count})</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/omnichannel-billing/customers" className="text-blue-600 hover:underline text-sm mb-2 block">Manage Customers &rarr;</Link>
          <h1 className="text-2xl font-bold">Executive Dashboard</h1>
          <p className="text-gray-600 dark:text-gray-400">High-level KPIs, best-selling products, and top customers.</p>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {data ? (
          <>
            {renderList('Top Products', data.top_products)}
            {renderList('Top Customers', data.top_customers)}
            {renderList('Top Channels', data.top_channels)}
          </>
        ) : (
          <p className="text-sm text-gray-500 col-span-3">Loading...</p>
        )}
      </div>
    </div>
  );
}
