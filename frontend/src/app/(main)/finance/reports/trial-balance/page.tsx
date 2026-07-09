/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";
import React, { useState, useEffect } from 'react';

export default function TrialBalancePage() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    setTimeout(() => {
      setData({
        lines: [
          { account_code: '1000', account_name: 'Cash Equivalents', account_type: 'asset', closing_debit: 575000, closing_credit: 0 },
          { account_code: '1200', account_name: 'Accounts Receivable', account_type: 'asset', closing_debit: 65000, closing_credit: 0 },
          { account_code: '2000', account_name: 'Accounts Payable', account_type: 'liability', closing_debit: 0, closing_credit: 17550 },
          { account_code: '3000', account_name: 'Owner Equity', account_type: 'equity', closing_debit: 0, closing_credit: 542450 },
          { account_code: '4000', account_name: 'Product Sales', account_type: 'income', closing_debit: 0, closing_credit: 850000 },
          { account_code: '5000', account_name: 'Payroll Expense', account_type: 'expense', closing_debit: 250000, closing_credit: 0 },
          { account_code: '5100', account_name: 'Cost of Goods Sold', account_type: 'expense', closing_debit: 450000, closing_credit: 0 },
          { account_code: '5200', account_name: 'Rent', account_type: 'expense', closing_debit: 60000, closing_credit: 0 },
          { account_code: '5300', account_name: 'Marketing', account_type: 'expense', closing_debit: 10000, closing_credit: 0 },
        ],
        total_debit: 1410000,
        total_credit: 1410000
      });
    }, 500);
  }, []);

  if (!data) return <div className="p-6">Loading statement...</div>;

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex justify-between items-center mb-6 border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold">Trial Balance</h1>
          <p className="text-gray-500 text-sm">Real-time ledger aggregation</p>
        </div>
        <button className="bg-gray-100 text-gray-700 px-4 py-2 rounded shadow hover:bg-gray-200">Export PDF</button>
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
            {data.lines.map((line: any, idx: number) => (
              <tr key={idx} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{line.account_code}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{line.account_name}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 capitalize">{line.account_type}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium text-gray-900">
                  {line.closing_debit > 0 ? `$${line.closing_debit.toLocaleString()}` : '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium text-gray-900">
                  {line.closing_credit > 0 ? `$${line.closing_credit.toLocaleString()}` : '-'}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot className="bg-gray-100">
            <tr>
              <th colSpan={3} className="px-6 py-4 text-right text-sm font-bold text-gray-900">Totals:</th>
              <th className="px-6 py-4 text-right text-sm font-bold text-green-700">${data.total_debit.toLocaleString()}</th>
              <th className="px-6 py-4 text-right text-sm font-bold text-green-700">${data.total_credit.toLocaleString()}</th>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}
