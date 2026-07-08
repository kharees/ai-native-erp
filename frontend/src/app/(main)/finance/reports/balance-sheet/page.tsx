"use client";
import React, { useState, useEffect } from 'react';

export default function BalanceSheetPage() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    setTimeout(() => {
      setData({
        assets: [
          { category_name: 'Cash and Cash Equivalents', amount: 575000 },
          { category_name: 'Accounts Receivable', amount: 65000 },
          { category_name: 'Inventory', amount: 120000 },
          { category_name: 'Property, Plant & Equipment', amount: 450000 }
        ],
        total_assets: 1210000,
        liabilities: [
          { category_name: 'Accounts Payable', amount: 17550 },
          { category_name: 'Short-term Debt', amount: 50000 },
          { category_name: 'Long-term Debt', amount: 250000 }
        ],
        total_liabilities: 317550,
        equity: [
          { category_name: 'Owner Equity', amount: 542450 },
          { category_name: 'Retained Earnings', amount: 350000 }
        ],
        total_equity: 892450
      });
    }, 500);
  }, []);

  if (!data) return <div className="p-6">Loading statement...</div>;

  const renderSection = (title: string, lines: any[], totalTitle: string, totalAmount: number) => (
    <div className="mb-6 border rounded-lg overflow-hidden">
      <div className="bg-gray-100 px-4 py-2 border-b font-bold text-gray-700">{title}</div>
      <div className="p-4 bg-white">
        {lines.map((line, idx) => (
          <div key={idx} className="flex justify-between py-1 text-sm text-gray-600 hover:bg-gray-50">
            <span>{line.category_name}</span>
            <span>${line.amount.toLocaleString()}</span>
          </div>
        ))}
      </div>
      <div className="bg-gray-50 px-4 py-3 border-t flex justify-between font-bold text-gray-900">
        <span>{totalTitle}</span>
        <span>${totalAmount.toLocaleString()}</span>
      </div>
    </div>
  );

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex justify-between items-center mb-6 border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold">Balance Sheet</h1>
          <p className="text-gray-500 text-sm">As of Today</p>
        </div>
        <button className="bg-gray-100 text-gray-700 px-4 py-2 rounded shadow hover:bg-gray-200">Export PDF</button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          {renderSection('Assets', data.assets, 'Total Assets', data.total_assets)}
        </div>
        <div>
          {renderSection('Liabilities', data.liabilities, 'Total Liabilities', data.total_liabilities)}
          {renderSection('Equity', data.equity, 'Total Equity', data.total_equity)}
          
          <div className={`p-4 rounded-lg font-bold flex justify-between ${data.total_assets === (data.total_liabilities + data.total_equity) ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
            <span>Total Liabilities & Equity</span>
            <span>${(data.total_liabilities + data.total_equity).toLocaleString()}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
