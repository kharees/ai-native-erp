'use client';

import { useEffect, useState } from 'react';
import apiClient from '@/lib/apiClient';

interface DashboardSummary {
  revenue: number;
  netProfit: number;
  operatingMargin: number;
}

interface ARLedger {
  outstanding_amount: number;
}

interface APVendor {
  outstanding_amount: number;
}

export default function FinancialDashboard() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [arOutstanding, setArOutstanding] = useState(0);
  const [apOutstanding, setApOutstanding] = useState(0);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([
      apiClient.get('/api/v1/finance-reports/dashboard-summary'),
      apiClient.get<ARLedger[]>('/api/v1/finance-ar-ap/ar/ledgers'),
      apiClient.get<APVendor[]>('/api/v1/finance-ar-ap/ap/vendors'),
    ])
      .then(([summaryRes, arRes, apRes]) => {
        setSummary(summaryRes.data);
        setArOutstanding(arRes.data.reduce((sum, l) => sum + Number(l.outstanding_amount), 0));
        setApOutstanding(apRes.data.reduce((sum, v) => sum + Number(v.outstanding_amount), 0));
      })
      .catch(() => setError('Failed to load financial dashboard'));
  }, []);

  if (error) return <div className="p-6 text-red-600">{error}</div>;
  if (!summary) return <div className="p-6">Loading dashboard...</div>;

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Enterprise Financial Dashboard</h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-white p-4 shadow rounded-lg border-t-4 border-blue-500">
          <p className="text-sm text-gray-500 font-medium">Total Revenue (YTD)</p>
          <p className="text-3xl font-bold">${Number(summary.revenue).toLocaleString()}</p>
        </div>
        <div className="bg-white p-4 shadow rounded-lg border-t-4 border-green-500">
          <p className="text-sm text-gray-500 font-medium">Net Profit (YTD)</p>
          <p className="text-3xl font-bold text-green-600">${Number(summary.netProfit).toLocaleString()}</p>
          <p className="text-xs text-gray-400 mt-1">{summary.operatingMargin}% Margin</p>
        </div>
        <div className="bg-white p-4 shadow rounded-lg border-t-4 border-indigo-500">
          <p className="text-sm text-gray-500 font-medium">Net AR - AP Position</p>
          <p className="text-3xl font-bold">${(arOutstanding - apOutstanding).toLocaleString()}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-bold mb-4 border-b pb-2">Receivables vs Payables</h2>
          <div className="flex justify-between items-center mb-2">
            <span className="text-gray-600">Accounts Receivable (You are owed)</span>
            <span className="font-bold text-green-600">${arOutstanding.toLocaleString()}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-gray-600">Accounts Payable (You owe)</span>
            <span className="font-bold text-red-600">${apOutstanding.toLocaleString()}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
