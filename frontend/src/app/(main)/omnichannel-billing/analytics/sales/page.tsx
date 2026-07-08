import Link from 'next/link';

export default function SalesAnalyticsPage() {
  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/omnichannel-billing" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Billing Dashboard</Link>
          <h1 className="text-2xl font-bold">Sales Analytics</h1>
          <p className="text-gray-600 dark:text-gray-400">Deep dive into sales trends, branch performance, and item metrics.</p>
        </div>
        <div className="space-x-2">
          <button className="bg-gray-200 text-gray-800 px-4 py-2 rounded shadow hover:bg-gray-300">Export CSV</button>
          <button className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700">Generate PDF Report</button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-medium text-gray-500">Total Revenue (MTD)</h3>
          <p className="text-3xl font-bold text-gray-900 dark:text-gray-100">₹0.00</p>
        </div>
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-medium text-gray-500">Total Orders (MTD)</h3>
          <p className="text-3xl font-bold text-gray-900 dark:text-gray-100">0</p>
        </div>
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-medium text-gray-500">Avg. Order Value</h3>
          <p className="text-3xl font-bold text-gray-900 dark:text-gray-100">₹0.00</p>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-8 border border-gray-200 dark:border-gray-700 text-center text-gray-500">
        [Interactive Chart Area: Sales Trend Line]
      </div>
    </div>
  );
}
