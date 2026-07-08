import Link from 'next/link';

export default function OutstandingPage() {
  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/omnichannel-billing" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Billing Dashboard</Link>
          <h1 className="text-2xl font-bold">Outstanding Dashboard</h1>
          <p className="text-gray-600 dark:text-gray-400">View customer outstanding balances and agings.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-medium text-gray-500">Total Outstanding</h3>
          <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">₹0.00</p>
        </div>
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-medium text-gray-500">0 - 30 Days</h3>
          <p className="text-2xl font-bold text-green-600">₹0.00</p>
        </div>
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-medium text-gray-500">31 - 60 Days</h3>
          <p className="text-2xl font-bold text-yellow-600">₹0.00</p>
        </div>
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-medium text-gray-500">90+ Days Overdue</h3>
          <p className="text-2xl font-bold text-red-600">₹0.00</p>
        </div>
      </div>
    </div>
  );
}
