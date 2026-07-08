import Link from 'next/link';

export default function AnalyticsDashboardPage() {
  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/omnichannel-billing" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Billing Dashboard</Link>
          <h1 className="text-2xl font-bold">Executive Dashboard</h1>
          <p className="text-gray-600 dark:text-gray-400">High-level KPIs, best-selling products, and top customers.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
         <div className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700">
             <div className="p-4 border-b">
                 <h2 className="font-bold">Top Products</h2>
             </div>
             <div className="p-4 text-center text-sm text-gray-500">
                 No data available.
             </div>
         </div>
         <div className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700">
             <div className="p-4 border-b">
                 <h2 className="font-bold">Top Customers</h2>
             </div>
             <div className="p-4 text-center text-sm text-gray-500">
                 No data available.
             </div>
         </div>
         <div className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700">
             <div className="p-4 border-b">
                 <h2 className="font-bold">Channel Performance</h2>
             </div>
             <div className="p-4 text-center text-sm text-gray-500">
                 No data available.
             </div>
         </div>
      </div>
    </div>
  );
}
