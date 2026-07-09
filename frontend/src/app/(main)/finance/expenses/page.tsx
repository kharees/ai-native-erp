/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import React, { useState, useEffect } from 'react';

export default function ExpensesPage() {
  const [expenses, setExpenses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setTimeout(() => {
      setExpenses([
        { id: '1', employee: 'Alice Smith', category: 'Travel', amount: 1250.00, date: '2026-07-02', status: 'Submitted' },
        { id: '2', employee: 'Bob Johnson', category: 'Office Supplies', amount: 45.00, date: '2026-07-03', status: 'Approved' },
        { id: '3', employee: 'Charlie Davis', category: 'Meals', amount: 120.00, date: '2026-07-04', status: 'Rejected' },
        { id: '4', employee: 'Alice Smith', category: 'Client Entertainment', amount: 450.00, date: '2026-06-28', status: 'Paid' },
      ]);
      setLoading(false);
    }, 500);
  }, []);

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Expense Management</h1>
        <button className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700">Submit Claim</button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white p-4 shadow rounded-lg border-l-4 border-yellow-500">
          <p className="text-sm text-gray-500 font-medium">Pending Approval</p>
          <p className="text-2xl font-bold text-yellow-600">3</p>
        </div>
        <div className="bg-white p-4 shadow rounded-lg border-l-4 border-green-500">
          <p className="text-sm text-gray-500 font-medium">Approved (Unpaid)</p>
          <p className="text-2xl font-bold">12</p>
        </div>
        <div className="bg-white p-4 shadow rounded-lg border-l-4 border-blue-500">
          <p className="text-sm text-gray-500 font-medium">Paid This Month</p>
          <p className="text-2xl font-bold">$4,250.00</p>
        </div>
      </div>

      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Employee</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Category</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Amount</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {loading ? (
              <tr><td colSpan={6} className="px-6 py-4 text-center">Loading...</td></tr>
            ) : (
              expenses.map((item: any) => (
                <tr key={item.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{item.date}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{item.employee}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{item.category}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium">${item.amount.toFixed(2)}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      item.status === 'Approved' ? 'bg-green-100 text-green-800' :
                      item.status === 'Paid' ? 'bg-blue-100 text-blue-800' :
                      item.status === 'Rejected' ? 'bg-red-100 text-red-800' :
                      'bg-yellow-100 text-yellow-800'
                    }`}>{item.status}</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                    {item.status === 'Submitted' && (
                      <>
                        <button className="text-green-600 hover:text-green-900 mr-2">Approve</button>
                        <button className="text-red-600 hover:text-red-900">Reject</button>
                      </>
                    )}
                    {item.status === 'Approved' && (
                      <button className="text-blue-600 hover:text-blue-900">Mark Paid</button>
                    )}
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
