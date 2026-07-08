'use client';
import { useState } from 'react';
import Link from 'next/link';

export default function StockMovementPage() {
  const [txnType, setTxnType] = useState('IN');

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div className="flex justify-between items-center">
        <div>
          <Link href="/universal-inventory" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Inventory Dashboard</Link>
          <h1 className="text-3xl font-bold">Universal Stock Engine</h1>
          <p className="text-gray-500 text-sm mt-1">Execute multi-warehouse inventory movements.</p>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md border border-gray-200 dark:border-gray-700">
        <h2 className="text-lg font-semibold mb-4 border-b pb-2 dark:border-gray-700">New Transaction</h2>
        <form className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Transaction Type</label>
              <select 
                value={txnType} 
                onChange={(e) => setTxnType(e.target.value)} 
                className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600"
              >
                <option value="IN">Stock In (GRN)</option>
                <option value="OUT">Stock Out (GI)</option>
                <option value="TRANSFER">Transfer</option>
                <option value="ADJUST">Adjustment</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Item ID</label>
              <input type="text" placeholder="Select Item..." className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Warehouse</label>
              <input type="text" placeholder="Select Warehouse..." className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Quantity</label>
              <input type="number" min="0.0001" step="0.0001" className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
            </div>
          </div>

          <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
            <h3 className="text-md font-medium mb-2">Dynamic Transaction Metadata</h3>
            <p className="text-xs text-gray-500 mb-4">Attach schema-less metadata directly to this movement (e.g., Driver Name, Vehicle Number, Supplier Batch ID).</p>
            
            <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 flex gap-2">
                <input type="text" placeholder="Metadata Key" className="flex-1 p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
                <input type="text" placeholder="Value" className="flex-1 p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
                <button type="button" className="bg-gray-200 dark:bg-gray-700 px-4 py-2 rounded text-sm hover:bg-gray-300 transition-colors">Add</button>
            </div>
          </div>

          <div className="flex justify-end pt-4">
            <button type="button" className="px-6 py-2 bg-green-600 text-white rounded hover:bg-green-700 font-medium">Execute Movement</button>
          </div>
        </form>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden border border-gray-200 dark:border-gray-700">
        <h3 className="p-4 font-semibold border-b dark:border-gray-700">Recent Transactions</h3>
        <table className="min-w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
            <tr>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Timestamp</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Type</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Item</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Qty</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Warehouse</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            <tr>
              <td className="px-6 py-4 text-center text-gray-500" colSpan={5}>No transactions recorded.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
