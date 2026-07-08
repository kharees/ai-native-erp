import Link from 'next/link';

export default function SerialsDashboard() {
  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/universal-inventory" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Inventory Dashboard</Link>
          <h1 className="text-3xl font-bold">Serial Number Tracking</h1>
          <p className="text-gray-500 text-sm mt-1">Trace individual unit histories, warranties, and exact locations.</p>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow mb-6 border border-gray-200 dark:border-gray-700 flex gap-4">
          <input type="text" placeholder="Search Serial Number..." className="flex-1 p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
          <input type="text" placeholder="Filter by Item ID..." className="flex-1 p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
          <button className="bg-blue-600 text-white px-6 py-2 rounded shadow hover:bg-blue-700 transition-colors">Trace</button>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden border border-gray-200 dark:border-gray-700">
        <table className="min-w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
            <tr>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Serial Number</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Item ID</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Status</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Current Warehouse</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Warranty Expiry</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            <tr>
              <td className="px-6 py-4 text-center text-gray-500" colSpan={5}>No serials found.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
