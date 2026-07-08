import Link from 'next/link';

export default function WarehousesDashboard() {
  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/universal-inventory" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Inventory Dashboard</Link>
          <h1 className="text-3xl font-bold">Universal Warehousing</h1>
        </div>
        <div className="space-x-2">
            <Link href="/universal-inventory/warehouses/bins">
              <button className="bg-gray-200 text-gray-800 px-4 py-2 rounded shadow hover:bg-gray-300 transition-colors">Manage Bins</button>
            </Link>
            <button className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700 transition-colors">Create Warehouse</button>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden border border-gray-200 dark:border-gray-700">
        <table className="min-w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
            <tr>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Warehouse Code</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Name</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Type</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Capacity</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            <tr>
              <td className="px-6 py-4 text-center text-gray-500" colSpan={5}>No warehouses found. Configure your first location.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
