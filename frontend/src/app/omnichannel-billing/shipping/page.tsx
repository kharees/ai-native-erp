import Link from 'next/link';

export default function ShippingPage() {
  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/omnichannel-billing" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Billing Dashboard</Link>
          <h1 className="text-2xl font-bold">Shipping & Logistics Manager</h1>
          <p className="text-gray-600 dark:text-gray-400">Track couriers, AWBs, and delivery statuses.</p>
        </div>
        <button className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700 transition-colors">
          Dispatch Order
        </button>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden border border-gray-200 dark:border-gray-700">
        <table className="min-w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
            <tr>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Order ID</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Courier</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">AWB Tracking No</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Dispatch Status</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            <tr>
              <td className="px-6 py-4 text-center text-gray-500" colSpan={5}>No dispatched orders found.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
