'use client';

import { useEffect, useState } from 'react';
import apiClient from '@/lib/apiClient';

interface TrialBalanceLine {
  account_code: string;
  account_name: string;
  account_type: string;
  closing_debit: number;
  closing_credit: number;
}

interface TrialBalanceReport {
  lines: TrialBalanceLine[];
  total_debit: number;
  total_credit: number;
}

export default function TrialBalancePage() {
  const [data, setData] = useState<TrialBalanceReport | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    apiClient
      .get('/api/v1/finance-reports/trial-balance')
      .then((res) => setData(res.data))
      .catch(() => setError('Failed to load trial balance'));
  }, []);

  if (error) return <div className="p-6 text-red-600">{error}</div>;
  if (!data) return <div className="p-6">Loading statement...</div>;

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex justify-between items-center mb-6 border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold">Trial Balance</h1>
          <p className="text-gray-500 text-sm">Real-time ledger aggregation</p>
        </div>
      </div>

      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Account Code</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Account Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Debit Balance</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Credit Balance</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {data.lines.length === 0 ? (
              <tr><td colSpan={5} className="px-6 py-4 text-center text-gray-500">No account activity found.</td></tr>
            ) : data.lines.map((line, idx) => (
              <tr key={idx} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{line.account_code}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{line.account_name}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 capitalize">{line.account_type}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium text-gray-900">
                  {line.closing_debit > 0 ? `$${Number(line.closing_debit).toLocaleString()}` : '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium text-gray-900">
                  {line.closing_credit > 0 ? `$${Number(line.closing_credit).toLocaleString()}` : '-'}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot className="bg-gray-100">
            <tr>
              <th colSpan={3} className="px-6 py-4 text-right text-sm font-bold text-gray-900">Totals:</th>
              <th className="px-6 py-4 text-right text-sm font-bold text-green-700">${Number(data.total_debit).toLocaleString()}</th>
              <th className="px-6 py-4 text-right text-sm font-bold text-green-700">${Number(data.total_credit).toLocaleString()}</th>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}
