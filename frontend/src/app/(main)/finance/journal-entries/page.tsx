/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import React, { useState, useEffect } from 'react';

export default function JournalEntriesPage() {
  const [vouchers, setVouchers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setTimeout(() => {
      setVouchers([
        { id: '1', voucher_number: 'JV-2026-0001', date: '2026-07-01', reference: 'Opening Balances', status: 'Posted', total: 50000.00 },
        { id: '2', voucher_number: 'JV-2026-0002', date: '2026-07-02', reference: 'Rent Payment', status: 'Posted', total: 12000.00 },
        { id: '3', voucher_number: 'JV-2026-0003', date: '2026-07-03', reference: 'INV-1001 Auto Post', status: 'Posted', total: 15000.00 },
        { id: '4', voucher_number: 'JV-2026-0004', date: '2026-07-05', reference: 'Petty Cash Replenish', status: 'Pending Approval', total: 500.00 },
        { id: '5', voucher_number: 'JV-2026-0005', date: '2026-07-06', reference: 'Depreciation Run', status: 'Draft', total: 1250.00 },
      ]);
      setLoading(false);
    }, 500);
  }, []);

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Journal Entries</h1>
        <button className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700">
          + Create Journal Entry
        </button>
      </div>

      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Voucher #</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Reference</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Total Amount</th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {loading ? (
              <tr>
                <td colSpan={6} className="px-6 py-4 text-center">Loading journal vouchers...</td>
              </tr>
            ) : (
              vouchers.map((voucher: any) => (
                <tr key={voucher.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-blue-600 cursor-pointer">{voucher.voucher_number}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{voucher.date}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{voucher.reference}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      voucher.status === 'Posted' ? 'bg-green-100 text-green-800' :
                      voucher.status === 'Draft' ? 'bg-gray-100 text-gray-800' :
                      'bg-yellow-100 text-yellow-800'
                    }`}>
                      {voucher.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium text-gray-900">
                    ${voucher.total.toFixed(2)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                    <button className="text-blue-600 hover:text-blue-900 mr-3">View</button>
                    {voucher.status !== 'Posted' && (
                      <button className="text-green-600 hover:text-green-900">Approve</button>
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
