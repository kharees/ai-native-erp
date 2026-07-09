/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import React, { useState, useEffect } from 'react';

export default function GeneralLedgerPage() {
  const [entries, setEntries] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedAccount, setSelectedAccount] = useState('all');

  useEffect(() => {
    setTimeout(() => {
      setEntries([
        { id: '1', date: '2026-07-01', description: 'Opening Balance', account: 'Cash', debit: 50000, credit: 0, balance: 50000 },
        { id: '2', date: '2026-07-02', description: 'Rent Payment', account: 'Rent Expense', debit: 12000, credit: 0, balance: 12000 },
        { id: '3', date: '2026-07-02', description: 'Rent Payment', account: 'Cash', debit: 0, credit: 12000, balance: 38000 },
        { id: '4', date: '2026-07-03', description: 'Invoice #INV-1001', account: 'Accounts Receivable', debit: 15000, credit: 0, balance: 15000 },
        { id: '5', date: '2026-07-03', description: 'Invoice #INV-1001', account: 'Sales Revenue', debit: 0, credit: 15000, balance: -15000 },
      ]);
      setLoading(false);
    }, 500);
  }, []);

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">General Ledger</h1>
        <div className="flex space-x-4">
          <select 
            className="border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm px-4 py-2"
            value={selectedAccount}
            onChange={(e) => setSelectedAccount(e.target.value)}
          >
            <option value="all">All Accounts</option>
            <option value="cash">Cash (1000)</option>
            <option value="ar">Accounts Receivable (1200)</option>
            <option value="sales">Sales Revenue (3000)</option>
          </select>
          <button className="bg-gray-100 text-gray-700 px-4 py-2 rounded shadow hover:bg-gray-200">
            Export PDF
          </button>
        </div>
      </div>

      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Account</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Description</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Debit</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Credit</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Running Balance</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {loading ? (
              <tr>
                <td colSpan={6} className="px-6 py-4 text-center">Loading ledger entries...</td>
              </tr>
            ) : (
              entries.map((entry: any) => (
                <tr key={entry.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{entry.date}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{entry.account}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{entry.description}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900">
                    {entry.debit > 0 ? `$${entry.debit.toFixed(2)}` : '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900">
                    {entry.credit > 0 ? `$${entry.credit.toFixed(2)}` : '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium text-gray-900">
                    ${Math.abs(entry.balance).toFixed(2)} {entry.balance < 0 ? 'CR' : 'DR'}
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
