import Link from 'next/link';

export default function ReportsDashboard() {
  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/universal-inventory" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Inventory Dashboard</Link>
          <h1 className="text-3xl font-bold">Executive Inventory Analytics</h1>
          <p className="text-gray-500 text-sm mt-1">Real-time valuation, aging, and KPI tracking.</p>
        </div>
        <div className="space-x-2">
            <Link href="/universal-inventory/reports/standard">
                <button className="bg-gray-200 text-gray-800 px-4 py-2 rounded shadow hover:bg-gray-300 transition-colors">Standard Reports (CSV)</button>
            </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6 shadow">
            <h3 className="text-gray-500 dark:text-gray-400 font-semibold mb-2 text-sm uppercase tracking-wider">Total Inventory Value</h3>
            <p className="text-3xl font-bold text-gray-900 dark:text-white">$1,245,000</p>
        </div>
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6 shadow">
            <h3 className="text-gray-500 dark:text-gray-400 font-semibold mb-2 text-sm uppercase tracking-wider">Total Items on Hand</h3>
            <p className="text-3xl font-bold text-gray-900 dark:text-white">45,230</p>
        </div>
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6 shadow">
            <h3 className="text-gray-500 dark:text-gray-400 font-semibold mb-2 text-sm uppercase tracking-wider">Dead Stock (180+ Days)</h3>
            <p className="text-3xl font-bold text-red-600">12%</p>
        </div>
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6 shadow">
            <h3 className="text-gray-500 dark:text-gray-400 font-semibold mb-2 text-sm uppercase tracking-wider">Turnover Ratio</h3>
            <p className="text-3xl font-bold text-green-600">4.2x</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700">
              <h3 className="font-bold text-lg mb-4">ABC Analysis (Pareto Distribution)</h3>
              <div className="h-64 bg-gray-100 dark:bg-gray-900 rounded flex items-center justify-center border border-dashed border-gray-300 dark:border-gray-700">
                  <p className="text-gray-500">[Pie Chart Placeholder: Class A (80%), B (15%), C (5%)]</p>
              </div>
          </div>
          
          <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700">
              <h3 className="font-bold text-lg mb-4">Inventory Aging Profile</h3>
              <div className="h-64 bg-gray-100 dark:bg-gray-900 rounded flex items-center justify-center border border-dashed border-gray-300 dark:border-gray-700">
                  <p className="text-gray-500">[Bar Chart Placeholder: 0-30, 31-90, 91-180, 180+ days]</p>
              </div>
          </div>
      </div>
    </div>
  );
}
