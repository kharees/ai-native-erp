'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import apiClient from '@/lib/apiClient';

interface Customer {
  id: string;
  name: string;
}

interface CollectionStatus {
  customer_id: string;
  customer_name: string;
  credit_limit: number;
  total_outstanding: number;
  overdue_amount: number;
  isOnCreditHold: boolean;
}

export default function CollectionsPage() {
  const [statuses, setStatuses] = useState<CollectionStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    apiClient
      .get('/api/v1/omnichannel-billing/customers/')
      .then(async (custRes) => {
        const customers: Customer[] = custRes.data.items || [];
        const results = await Promise.all(
          customers.map((c) =>
            apiClient
              .get<CollectionStatus>(`/api/v1/omnichannel-billing/collections/status/${c.id}`)
              .then((r) => r.data)
              .catch(() => null)
          )
        );
        setStatuses(results.filter((r): r is CollectionStatus => r !== null && r.overdue_amount > 0));
      })
      .catch(() => setError('Failed to load collections'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/omnichannel-billing/analytics/dashboard" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Billing Dashboard</Link>
          <h1 className="text-2xl font-bold">Collections Console</h1>
          <p className="text-gray-600 dark:text-gray-400">Customers with overdue balances requiring follow-up.</p>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden border border-gray-200 dark:border-gray-700">
        <table className="min-w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
            <tr>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Customer</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Credit Limit</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Total Due</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Overdue</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Credit Hold Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {loading ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={5}>Loading collections...</td></tr>
            ) : statuses.length === 0 ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={5}>No collection items require attention.</td></tr>
            ) : statuses.map((s) => (
              <tr key={s.customer_id}>
                <td className="px-6 py-4 font-medium">{s.customer_name}</td>
                <td className="px-6 py-4 text-gray-500">${Number(s.credit_limit).toFixed(2)}</td>
                <td className="px-6 py-4">${Number(s.total_outstanding).toFixed(2)}</td>
                <td className="px-6 py-4 text-red-600 font-medium">${Number(s.overdue_amount).toFixed(2)}</td>
                <td className="px-6 py-4">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${s.isOnCreditHold ? 'bg-red-50 text-red-700 border border-red-200' : 'bg-emerald-50 text-emerald-700 border border-emerald-200'}`}>
                    {s.isOnCreditHold ? 'On Hold' : 'Clear'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
