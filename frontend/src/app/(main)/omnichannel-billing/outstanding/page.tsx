'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import apiClient from '@/lib/apiClient';

interface Customer {
  id: string;
  name: string;
}

interface AgingBucket {
  bucket_0_30: number;
  bucket_31_60: number;
  bucket_61_90: number;
  bucket_90_plus: number;
  total: number;
}

const ZERO: AgingBucket = { bucket_0_30: 0, bucket_31_60: 0, bucket_61_90: 0, bucket_90_plus: 0, total: 0 };

export default function OutstandingPage() {
  const [totals, setTotals] = useState<AgingBucket>(ZERO);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    apiClient
      .get('/api/v1/omnichannel-billing/customers/')
      .then(async (custRes) => {
        const customers: Customer[] = custRes.data.items || [];
        const agingResults = await Promise.all(
          customers.map((c) =>
            apiClient
              .get<AgingBucket>(`/api/v1/omnichannel-billing/collections/aging/${c.id}`)
              .then((r) => r.data)
              .catch(() => ZERO)
          )
        );
        const sum = agingResults.reduce(
          (acc, a) => ({
            bucket_0_30: acc.bucket_0_30 + Number(a.bucket_0_30),
            bucket_31_60: acc.bucket_31_60 + Number(a.bucket_31_60),
            bucket_61_90: acc.bucket_61_90 + Number(a.bucket_61_90),
            bucket_90_plus: acc.bucket_90_plus + Number(a.bucket_90_plus),
            total: acc.total + Number(a.total),
          }),
          { ...ZERO }
        );
        setTotals(sum);
      })
      .catch(() => setError('Failed to load outstanding balances'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/omnichannel-billing/analytics/dashboard" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Billing Dashboard</Link>
          <h1 className="text-2xl font-bold">Outstanding Dashboard</h1>
          <p className="text-gray-600 dark:text-gray-400">Customer outstanding balances and aging, aggregated across all customers.</p>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-medium text-gray-500">Total Outstanding</h3>
          <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{loading ? '-' : `$${totals.total.toFixed(2)}`}</p>
        </div>
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-medium text-gray-500">0 - 30 Days</h3>
          <p className="text-2xl font-bold text-green-600">{loading ? '-' : `$${totals.bucket_0_30.toFixed(2)}`}</p>
        </div>
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-medium text-gray-500">31 - 90 Days</h3>
          <p className="text-2xl font-bold text-yellow-600">{loading ? '-' : `$${(totals.bucket_31_60 + totals.bucket_61_90).toFixed(2)}`}</p>
        </div>
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-medium text-gray-500">90+ Days Overdue</h3>
          <p className="text-2xl font-bold text-red-600">{loading ? '-' : `$${totals.bucket_90_plus.toFixed(2)}`}</p>
        </div>
      </div>
    </div>
  );
}
