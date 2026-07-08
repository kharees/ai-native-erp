"use client";

import React, { useState, useEffect } from 'react';

export default function AccountsReceivablePage() {
  const [ar, setAr] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setTimeout(() => {
      setAr([
        { id: '1', customer: 'Acme Corp', outstanding: 15000.00, creditLimit: 50000.00, aging30: 0, aging60: 15000, aging90: 0, status: 'Active' },
        { id: '2', customer: 'Stark Industries', outstanding: 45000.00, creditLimit: 100000.00, aging30: 25000, aging60: 20000, aging90: 0, status: 'Active' },
        { id: '3', customer: 'Wayne Enterprises', outstanding: 5000.00, creditLimit: 5000.00, aging30: 0, aging60: 0, aging90: 5000, status: 'Warning - High Risk' },
      ]);
      setLoading(false);
    }, 500);
  }, []);

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Accounts Receivable (AR)</h1>
        <div className="flex space-x-2">
          <button className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700">Record Receipt</button>
          <button className="bg-gray-100 text-gray-700 px-4 py-2 rounded shadow hover:bg-gray-200">Send Reminders</button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-white p-4 shadow rounded-lg border-l-4 border-blue-500">
          <p className="text-sm text-gray-500 font-medium">Total Outstanding</p>
          <p className="text-2xl font-bold">$65,000.00</p>
        </div>
        <div className="bg-white p-4 shadow rounded-lg border-l-4 border-red-500">
          <p className="text-sm text-gray-500 font-medium">Overdue (90+ Days)</p>
          <p className="text-2xl font-bold text-red-600">$5,000.00</p>
        </div>
        <div className="bg-white p-4 shadow rounded-lg border-l-4 border-green-500">
          <p className="text-sm text-gray-500 font-medium">Collected This Month</p>
          <p className="text-2xl font-bold">$120,400.00</p>
        </div>
      </div>

      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Customer</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Outstanding</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">0-30 Days</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">31-60 Days</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">61-90+ Days</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Credit Limit</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {loading ? (
              <tr><td colSpan={7} className="px-6 py-4 text-center">Loading...</td></tr>
            ) : (
              ar.map((item: any) => (
                <tr key={item.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-blue-600 cursor-pointer">{item.customer}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium">${item.outstanding.toFixed(2)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right">${item.aging30.toFixed(2)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-yellow-600">${item.aging60.toFixed(2)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-red-600">${item.aging90.toFixed(2)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-500">${item.creditLimit.toFixed(2)}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      item.status === 'Active' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>{item.status}</span>
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
