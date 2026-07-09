"use client";
import React, { useState, useEffect } from 'react';

interface FinancialDashboardData {
  revenue: number;
  netProfit: number;
  operatingMargin: number;
  cashPosition: number;
  arOutstanding: number;
  apOutstanding: number;
}

export default function FinancialDashboard() {
  const [data, setData] = useState<FinancialDashboardData | null>(null);

  useEffect(() => {
    // Mock API call to /api/v1/finance-reports/dashboard-summary
    setTimeout(() => {
      setData({
        revenue: 1250000,
        netProfit: 350000,
        operatingMargin: 28,
        cashPosition: 575000,
        arOutstanding: 65000,
        apOutstanding: 17550
      });
    }, 500);
  }, []);

  if (!data) return <div className="p-6">Loading dashboard...</div>;

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Enterprise Financial Dashboard</h1>
        <button className="bg-gray-100 text-gray-700 px-4 py-2 rounded shadow hover:bg-gray-200">Export PDF</button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-white p-4 shadow rounded-lg border-t-4 border-blue-500">
          <p className="text-sm text-gray-500 font-medium">Total Revenue (YTD)</p>
          <p className="text-3xl font-bold">${data.revenue.toLocaleString()}</p>
        </div>
        <div className="bg-white p-4 shadow rounded-lg border-t-4 border-green-500">
          <p className="text-sm text-gray-500 font-medium">Net Profit (YTD)</p>
          <p className="text-3xl font-bold text-green-600">${data.netProfit.toLocaleString()}</p>
          <p className="text-xs text-gray-400 mt-1">{data.operatingMargin}% Margin</p>
        </div>
        <div className="bg-white p-4 shadow rounded-lg border-t-4 border-indigo-500">
          <p className="text-sm text-gray-500 font-medium">Current Cash Position</p>
          <p className="text-3xl font-bold">${data.cashPosition.toLocaleString()}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-bold mb-4 border-b pb-2">Receivables vs Payables</h2>
          <div className="flex justify-between items-center mb-2">
            <span className="text-gray-600">Accounts Receivable (You are owed)</span>
            <span className="font-bold text-green-600">${data.arOutstanding.toLocaleString()}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-gray-600">Accounts Payable (You owe)</span>
            <span className="font-bold text-red-600">${data.apOutstanding.toLocaleString()}</span>
          </div>
        </div>
        
        <div className="bg-white shadow rounded-lg p-6 flex items-center justify-center">
          <p className="text-gray-400 italic">[ Interactive Charts Placeholder ]</p>
        </div>
      </div>
    </div>
  );
}
