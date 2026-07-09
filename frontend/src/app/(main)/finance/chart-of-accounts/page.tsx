/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import React, { useState, useEffect } from 'react';

export default function ChartOfAccountsPage() {
  const [accounts, setAccounts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // In a real implementation, this would fetch from /api/v1/finance-core/accounts
    // For now, we simulate data to show the layout
    setTimeout(() => {
      setAccounts([
        { id: '1', account_code: '1000', name: 'Cash', type: 'Asset', status: 'Active', balance: 50000.00 },
        { id: '2', account_code: '1200', name: 'Accounts Receivable', type: 'Asset', status: 'Active', balance: 15000.00 },
        { id: '3', account_code: '2000', name: 'Accounts Payable', type: 'Liability', status: 'Active', balance: -8000.00 },
        { id: '4', account_code: '3000', name: 'Sales Revenue', type: 'Income', status: 'Active', balance: -120000.00 },
        { id: '5', account_code: '4000', name: 'Rent Expense', type: 'Expense', status: 'Active', balance: 12000.00 },
      ]);
      setLoading(false);
    }, 500);
  }, []);

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Chart of Accounts</h1>
        <button className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700">
          + New Account
        </button>
      </div>

      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Account Code</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Current Balance</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {loading ? (
              <tr>
                <td colSpan={5} className="px-6 py-4 text-center">Loading accounts...</td>
              </tr>
            ) : (
              accounts.map((acc: any) => (
                <tr key={acc.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{acc.account_code}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{acc.name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{acc.type}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                      {acc.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium text-gray-900">
                    ${Math.abs(acc.balance).toFixed(2)} {acc.balance < 0 ? 'CR' : 'DR'}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
