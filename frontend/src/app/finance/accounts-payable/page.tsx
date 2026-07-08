"use client";

import React, { useState, useEffect } from 'react';

export default function AccountsPayablePage() {
  const [ap, setAp] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setTimeout(() => {
      setAp([
        { id: '1', vendor: 'Tech Data Logistics', outstanding: 12500.00, dueNext7: 12500, dueNext30: 0, status: 'Pending Approval' },
        { id: '2', vendor: 'Global Supplies Inc', outstanding: 4200.00, dueNext7: 0, dueNext30: 4200, status: 'Approved' },
        { id: '3', vendor: 'AWS Cloud', outstanding: 850.00, dueNext7: 850, dueNext30: 0, status: 'Overdue' },
      ]);
      setLoading(false);
    }, 500);
  }, []);

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Accounts Payable (AP)</h1>
        <div className="flex space-x-2">
          <button className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700">Record Bill</button>
          <button className="bg-gray-100 text-gray-700 px-4 py-2 rounded shadow hover:bg-gray-200">Process Payments</button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-white p-4 shadow rounded-lg border-l-4 border-red-500">
          <p className="text-sm text-gray-500 font-medium">Total Outstanding</p>
          <p className="text-2xl font-bold">$17,550.00</p>
        </div>
        <div className="bg-white p-4 shadow rounded-lg border-l-4 border-yellow-500">
          <p className="text-sm text-gray-500 font-medium">Due in 7 Days</p>
          <p className="text-2xl font-bold text-yellow-600">$13,350.00</p>
        </div>
        <div className="bg-white p-4 shadow rounded-lg border-l-4 border-green-500">
          <p className="text-sm text-gray-500 font-medium">Paid This Month</p>
          <p className="text-2xl font-bold">$42,100.00</p>
        </div>
      </div>

      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Vendor</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Total Outstanding</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Due ≤ 7 Days</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Due 8-30 Days</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {loading ? (
              <tr><td colSpan={6} className="px-6 py-4 text-center">Loading...</td></tr>
            ) : (
              ap.map((item: any) => (
                <tr key={item.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-blue-600 cursor-pointer">{item.vendor}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium">${item.outstanding.toFixed(2)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-red-600">${item.dueNext7.toFixed(2)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right">${item.dueNext30.toFixed(2)}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      item.status === 'Approved' ? 'bg-green-100 text-green-800' :
                      item.status === 'Overdue' ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'
                    }`}>{item.status}</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                    <button className="text-indigo-600 hover:text-indigo-900 mr-2">Pay</button>
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
