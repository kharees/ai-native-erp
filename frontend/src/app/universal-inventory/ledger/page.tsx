import Link from 'next/link';

export default function LedgerDashboard() {
  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/universal-inventory" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Inventory Dashboard</Link>
          <h1 className="text-3xl font-bold">Universal Inventory Ledger</h1>
          <p className="text-gray-500 text-sm mt-1">Immutable stock history and valuation tracking.</p>
        </div>
        <div className="space-x-2">
            <button className="bg-gray-200 text-gray-800 px-4 py-2 rounded shadow hover:bg-gray-300 transition-colors">Export CSV</button>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow mb-6 border border-gray-200 dark:border-gray-700 flex gap-4">
          <input type="text" placeholder="Filter by Item ID..." className="flex-1 p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
          <input type="text" placeholder="Filter by Warehouse ID..." className="flex-1 p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
          <select className="p-2 border rounded dark:bg-gray-700 dark:border-gray-600">
              <option value="">All Reference Types</option>
              <option value="GRN">Goods Receipt Note</option>
              <option value="GI">Goods Issue</option>
              <option value="STR">Stock Transfer</option>
          </select>
          <button className="bg-blue-600 text-white px-6 py-2 rounded shadow hover:bg-blue-700 transition-colors">Search</button>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden border border-gray-200 dark:border-gray-700">
        <table className="min-w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
            <tr>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Date</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Item ID</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Warehouse</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Qty Before</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Movement</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Qty After</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Total Value</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            <tr>
              <td className="px-6 py-4 text-center text-gray-500" colSpan={7}>No ledger entries found.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
