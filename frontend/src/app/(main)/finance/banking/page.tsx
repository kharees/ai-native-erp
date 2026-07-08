"use client";

import React, { useState, useEffect } from 'react';

export default function BankingPage() {
  const [banks, setBanks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setTimeout(() => {
      setBanks([
        { id: '1', bank: 'Chase Business Checking', accountNo: '****1234', balance: 125000.00, lastReconciled: '2026-06-30' },
        { id: '2', bank: 'Bank of America Savings', accountNo: '****9876', balance: 450000.00, lastReconciled: '2026-06-30' },
        { id: '3', bank: 'Petty Cash', accountNo: 'N/A', balance: 1500.00, lastReconciled: '2026-07-01' },
      ]);
      setLoading(false);
    }, 500);
  }, []);

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Banking & Cash Management</h1>
        <div className="flex space-x-2">
          <button className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700">Import Statement</button>
          <button className="bg-green-600 text-white px-4 py-2 rounded shadow hover:bg-green-700">Bank Transfer</button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div className="bg-white p-4 shadow rounded-lg border-l-4 border-blue-500">
          <p className="text-sm text-gray-500 font-medium">Total Cash in Banks</p>
          <p className="text-2xl font-bold">$575,000.00</p>
        </div>
        <div className="bg-white p-4 shadow rounded-lg border-l-4 border-yellow-500">
          <p className="text-sm text-gray-500 font-medium">Items Pending Reconciliation</p>
          <p className="text-2xl font-bold text-yellow-600">14</p>
        </div>
      </div>

      <div className="bg-white shadow rounded-lg overflow-hidden mb-6">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-medium text-gray-900">Accounts Overview</h2>
        </div>
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Account Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Account Number</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Current Balance</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Last Reconciled</th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {loading ? (
              <tr><td colSpan={5} className="px-6 py-4 text-center">Loading...</td></tr>
            ) : (
              banks.map((item: any) => (
                <tr key={item.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{item.bank}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{item.accountNo}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium">${item.balance.toFixed(2)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{item.lastReconciled}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                    <button className="text-indigo-600 hover:text-indigo-900 mr-3">View Ledger</button>
                    <button className="text-blue-600 hover:text-blue-900">Reconcile</button>
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
