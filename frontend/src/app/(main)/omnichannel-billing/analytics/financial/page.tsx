import Link from 'next/link';

export default function FinancialAnalyticsPage() {
  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/omnichannel-billing" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Billing Dashboard</Link>
          <h1 className="text-2xl font-bold">Financial Analytics</h1>
          <p className="text-gray-600 dark:text-gray-400">Track collections, outstanding agings, and tax summaries.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700 border-t-4 border-t-red-500">
          <h3 className="text-sm font-medium text-gray-500">Total Outstanding</h3>
          <p className="text-3xl font-bold text-gray-900 dark:text-gray-100">₹0.00</p>
        </div>
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700 border-t-4 border-t-green-500">
          <h3 className="text-sm font-medium text-gray-500">Total Collected</h3>
          <p className="text-3xl font-bold text-gray-900 dark:text-gray-100">₹0.00</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
         <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-8 border border-gray-200 dark:border-gray-700 text-center text-gray-500">
            [Customer Aging Pie Chart]
         </div>
         <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-8 border border-gray-200 dark:border-gray-700 text-center text-gray-500">
            [Tax Summary (GST/IGST/SGST)]
         </div>
      </div>
    </div>
  );
}
