'use client';

import { useEffect, useState } from 'react';
import apiClient from '@/lib/apiClient';

interface CategoryLine {
  category_name: string;
  amount: number;
}

interface PLReport {
  revenue: CategoryLine[];
  cogs: CategoryLine[];
  gross_profit: number;
  operating_expenses: CategoryLine[];
  operating_profit: number;
  net_profit: number;
}

export default function ProfitAndLossPage() {
  const [data, setData] = useState<PLReport | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    apiClient
      .get('/api/v1/finance-reports/profit-and-loss')
      .then((res) => setData(res.data))
      .catch(() => setError('Failed to load profit & loss statement'));
  }, []);

  if (error) return <div className="p-6 text-red-600">{error}</div>;
  if (!data) return <div className="p-6">Loading statement...</div>;

  const renderSection = (title: string, lines: CategoryLine[], totalAmount: number) => (
    <div className="mb-4">
      <h3 className="font-bold text-gray-700 border-b pb-1 mb-2">{title}</h3>
      {lines.length === 0 ? (
        <p className="text-sm text-gray-400 pl-4">No entries.</p>
      ) : lines.map((line, idx) => (
        <div key={idx} className="flex justify-between py-1 text-sm text-gray-600 pl-4 hover:bg-gray-50">
          <span>{line.category_name}</span>
          <span>${Number(line.amount).toLocaleString()}</span>
        </div>
      ))}
      <div className="flex justify-between py-2 font-bold text-gray-800 border-t mt-1">
        <span>Total {title}</span>
        <span>${Number(totalAmount).toLocaleString()}</span>
      </div>
    </div>
  );

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-6 border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold">Profit & Loss Statement</h1>
          <p className="text-gray-500 text-sm">For the year to date</p>
        </div>
      </div>

      <div className="bg-white shadow rounded-lg p-8">
        {renderSection('Revenue', data.revenue, data.revenue.reduce((acc, v) => acc + Number(v.amount), 0))}
        {renderSection('Cost of Goods Sold (COGS)', data.cogs, data.cogs.reduce((acc, v) => acc + Number(v.amount), 0))}

        <div className="flex justify-between py-3 px-4 font-bold text-lg bg-green-50 rounded mb-6 text-green-900">
          <span>Gross Profit</span>
          <span>${Number(data.gross_profit).toLocaleString()}</span>
        </div>

        {renderSection('Operating Expenses', data.operating_expenses, data.operating_expenses.reduce((acc, v) => acc + Number(v.amount), 0))}

        <div className="flex justify-between py-3 px-4 font-bold text-xl bg-blue-50 rounded mt-6 text-blue-900 border-t-2 border-blue-200">
          <span>Net Profit</span>
          <span>${Number(data.net_profit).toLocaleString()}</span>
        </div>
      </div>
    </div>
  );
}
