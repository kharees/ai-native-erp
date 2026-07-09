/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";
import React, { useState, useEffect } from 'react';

export default function ProfitAndLossPage() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    setTimeout(() => {
      setData({
        revenue: [{ category_name: 'Product Sales', amount: 850000 }, { category_name: 'Service Revenue', amount: 400000 }],
        cogs: [{ category_name: 'Cost of Goods Sold', amount: 450000 }],
        gross_profit: 800000,
        operating_expenses: [
          { category_name: 'Payroll Expense', amount: 250000 },
          { category_name: 'Rent', amount: 60000 },
          { category_name: 'Marketing', amount: 140000 }
        ],
        operating_profit: 350000,
        net_profit: 350000
      });
    }, 500);
  }, []);

  if (!data) return <div className="p-6">Loading statement...</div>;

  const renderSection = (title: string, lines: any[], isTotal: boolean = false, totalAmount?: number) => (
    <div className="mb-4">
      <h3 className={`font-bold text-gray-700 border-b pb-1 mb-2 ${isTotal ? 'text-lg text-gray-900 mt-4' : ''}`}>{title}</h3>
      {!isTotal && lines.map((line, idx) => (
        <div key={idx} className="flex justify-between py-1 text-sm text-gray-600 pl-4 hover:bg-gray-50">
          <span>{line.category_name}</span>
          <span>${line.amount.toLocaleString()}</span>
        </div>
      ))}
      {totalAmount !== undefined && (
        <div className="flex justify-between py-2 font-bold text-gray-800 border-t mt-1">
          <span>Total {title}</span>
          <span>${totalAmount.toLocaleString()}</span>
        </div>
      )}
    </div>
  );

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-6 border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold">Profit & Loss Statement</h1>
          <p className="text-gray-500 text-sm">For the year to date</p>
        </div>
        <button className="bg-gray-100 text-gray-700 px-4 py-2 rounded shadow hover:bg-gray-200">Export</button>
      </div>

      <div className="bg-white shadow rounded-lg p-8">
        {renderSection('Revenue', data.revenue, false, data.revenue.reduce((acc: number, val: any) => acc + val.amount, 0))}
        {renderSection('Cost of Goods Sold (COGS)', data.cogs, false, data.cogs.reduce((acc: number, val: any) => acc + val.amount, 0))}
        
        <div className="flex justify-between py-3 px-4 font-bold text-lg bg-green-50 rounded mb-6 text-green-900">
          <span>Gross Profit</span>
          <span>${data.gross_profit.toLocaleString()}</span>
        </div>

        {renderSection('Operating Expenses', data.operating_expenses, false, data.operating_expenses.reduce((acc: number, val: any) => acc + val.amount, 0))}

        <div className="flex justify-between py-3 px-4 font-bold text-xl bg-blue-50 rounded mt-6 text-blue-900 border-t-2 border-blue-200">
          <span>Net Profit</span>
          <span>${data.net_profit.toLocaleString()}</span>
        </div>
      </div>
    </div>
  );
}
