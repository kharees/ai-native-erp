/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";
import React, { useState, useEffect } from 'react';

export default function BudgetingPage() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    setTimeout(() => {
      setData({
        budgets: [
          { id: '1', name: 'FY2026 Q1 Operating', period: 'QUARTERLY', status: 'ACTIVE', total_allocated: 450000 },
          { id: '2', name: 'FY2026 Annual Marketing', period: 'ANNUAL', status: 'DRAFT', total_allocated: 1200000 }
        ],
        variance: [
          { account: 'Payroll Expense', budget: 200000, actual: 195000, variance: 5000, variance_percent: 2.5 },
          { account: 'Marketing', budget: 50000, actual: 65000, variance: -15000, variance_percent: -30.0 },
          { account: 'Rent', budget: 20000, actual: 20000, variance: 0, variance_percent: 0.0 }
        ]
      });
    }, 500);
  }, []);

  if (!data) return <div className="p-6">Loading Budgets...</div>;

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold">Budget Management</h1>
          <p className="text-gray-500 text-sm">Planning and Variance Analysis</p>
        </div>
        <button className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700">+ Create Budget</button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-bold mb-4 border-b pb-2">Active Budgets</h2>
          <div className="space-y-4">
            {data.budgets.map((budget: any) => (
              <div key={budget.id} className="border p-4 rounded-lg hover:shadow-md transition">
                <div className="flex justify-between items-center mb-2">
                  <h3 className="font-bold text-gray-800">{budget.name}</h3>
                  <span className={`px-2 py-1 text-xs font-semibold rounded-full ${budget.status === 'ACTIVE' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                    {budget.status}
                  </span>
                </div>
                <div className="flex justify-between text-sm text-gray-600">
                  <span>Period: {budget.period}</span>
                  <span className="font-medium text-gray-900">Total: ${budget.total_allocated.toLocaleString()}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-bold mb-4 border-b pb-2">Budget vs Actual Variance (FY2026 Q1)</h2>
          <div className="space-y-3">
            {data.variance.map((item: any, idx: number) => (
              <div key={idx} className="flex justify-between items-center border-b pb-2 last:border-0">
                <div className="w-1/3 text-sm font-medium text-gray-700">{item.account}</div>
                <div className="w-1/4 text-sm text-right text-gray-500">B: ${item.budget.toLocaleString()}</div>
                <div className="w-1/4 text-sm text-right text-gray-500">A: ${item.actual.toLocaleString()}</div>
                <div className={`w-1/6 text-sm text-right font-bold ${item.variance < 0 ? 'text-red-600' : 'text-green-600'}`}>
                  {item.variance_percent > 0 ? '+' : ''}{item.variance_percent}%
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
