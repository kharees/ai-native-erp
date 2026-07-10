'use client';

import { useEffect, useState } from 'react';
import apiClient from '@/lib/apiClient';

interface CashFlowLine {
  description: string;
  amount: number;
}

interface CashFlowReport {
  operating_activities: CashFlowLine[];
  net_operating_cash: number;
  investing_activities: CashFlowLine[];
  net_investing_cash: number;
  financing_activities: CashFlowLine[];
  net_financing_cash: number;
  net_cash_increase: number;
  opening_cash_balance: number;
  closing_cash_balance: number;
}

export default function CashFlowPage() {
  const [data, setData] = useState<CashFlowReport | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    apiClient
      .get('/api/v1/finance-reports/cash-flow')
      .then((res) => setData(res.data))
      .catch(() => setError('Failed to load cash flow statement'));
  }, []);

  if (error) return <div className="p-6 text-red-600">{error}</div>;
  if (!data) return <div className="p-6">Loading statement...</div>;

  const renderSection = (title: string, lines: CashFlowLine[], totalTitle: string, totalAmount: number) => (
    <div className="mb-6">
      <h3 className="font-bold text-gray-800 bg-gray-100 px-4 py-2 rounded-t-lg">{title}</h3>
      <div className="bg-white p-4 border-x border-b rounded-b-lg">
        {lines.length === 0 ? (
          <p className="text-sm text-gray-400">No entries.</p>
        ) : lines.map((line, idx) => (
          <div key={idx} className="flex justify-between py-2 text-sm text-gray-700 border-b last:border-0 hover:bg-gray-50">
            <span>{line.description}</span>
            <span className={Number(line.amount) < 0 ? 'text-red-600' : 'text-gray-900'}>
              {Number(line.amount) < 0 ? `($${Math.abs(Number(line.amount)).toLocaleString()})` : `$${Number(line.amount).toLocaleString()}`}
            </span>
          </div>
        ))}
        <div className="flex justify-between py-3 mt-2 border-t-2 font-bold text-gray-900">
          <span>{totalTitle}</span>
          <span className={Number(totalAmount) < 0 ? 'text-red-600' : 'text-gray-900'}>
            {Number(totalAmount) < 0 ? `($${Math.abs(Number(totalAmount)).toLocaleString()})` : `$${Number(totalAmount).toLocaleString()}`}
          </span>
        </div>
      </div>
    </div>
  );

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-6 border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold">Statement of Cash Flows</h1>
          <p className="text-gray-500 text-sm">Indirect Method</p>
        </div>
      </div>

      <div className="flex justify-between py-4 px-6 font-bold text-lg bg-blue-50 rounded mb-6 text-blue-900">
        <span>Opening Cash Balance</span>
        <span>${Number(data.opening_cash_balance).toLocaleString()}</span>
      </div>

      {renderSection('Operating Activities', data.operating_activities, 'Net Cash from Operating Activities', data.net_operating_cash)}
      {renderSection('Investing Activities', data.investing_activities, 'Net Cash from Investing Activities', data.net_investing_cash)}
      {renderSection('Financing Activities', data.financing_activities, 'Net Cash from Financing Activities', data.net_financing_cash)}

      <div className="flex justify-between py-4 px-6 font-bold text-lg bg-green-50 rounded mt-6 text-green-900 border-t-4 border-green-200">
        <span>Closing Cash Balance</span>
        <span>${Number(data.closing_cash_balance).toLocaleString()}</span>
      </div>
    </div>
  );
}
