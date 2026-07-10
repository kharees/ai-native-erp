'use client';

import { useEffect, useState } from 'react';
import apiClient from '@/lib/apiClient';

interface CategoryLine {
  category_name: string;
  amount: number;
}

interface BalanceSheetReport {
  assets: CategoryLine[];
  total_assets: number;
  liabilities: CategoryLine[];
  total_liabilities: number;
  equity: CategoryLine[];
  total_equity: number;
}

export default function BalanceSheetPage() {
  const [data, setData] = useState<BalanceSheetReport | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    apiClient
      .get('/api/v1/finance-reports/balance-sheet')
      .then((res) => setData(res.data))
      .catch(() => setError('Failed to load balance sheet'));
  }, []);

  if (error) return <div className="p-6 text-red-600">{error}</div>;
  if (!data) return <div className="p-6">Loading statement...</div>;

  const renderSection = (title: string, lines: CategoryLine[], totalTitle: string, totalAmount: number) => (
    <div className="mb-6 border rounded-lg overflow-hidden">
      <div className="bg-gray-100 px-4 py-2 border-b font-bold text-gray-700">{title}</div>
      <div className="p-4 bg-white">
        {lines.length === 0 ? (
          <p className="text-sm text-gray-400">No entries.</p>
        ) : lines.map((line, idx) => (
          <div key={idx} className="flex justify-between py-1 text-sm text-gray-600 hover:bg-gray-50">
            <span>{line.category_name}</span>
            <span>${Number(line.amount).toLocaleString()}</span>
          </div>
        ))}
      </div>
      <div className="bg-gray-50 px-4 py-3 border-t flex justify-between font-bold text-gray-900">
        <span>{totalTitle}</span>
        <span>${Number(totalAmount).toLocaleString()}</span>
      </div>
    </div>
  );

  const balances = Number(data.total_assets) === Number(data.total_liabilities) + Number(data.total_equity);

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex justify-between items-center mb-6 border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold">Balance Sheet</h1>
          <p className="text-gray-500 text-sm">As of Today</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          {renderSection('Assets', data.assets, 'Total Assets', data.total_assets)}
        </div>
        <div>
          {renderSection('Liabilities', data.liabilities, 'Total Liabilities', data.total_liabilities)}
          {renderSection('Equity', data.equity, 'Total Equity', data.total_equity)}

          <div className={`p-4 rounded-lg font-bold flex justify-between ${balances ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
            <span>Total Liabilities & Equity</span>
            <span>${(Number(data.total_liabilities) + Number(data.total_equity)).toLocaleString()}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
