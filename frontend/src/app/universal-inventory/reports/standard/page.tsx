import Link from 'next/link';

export default function StandardReportsPage() {
  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/universal-inventory/reports" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Dashboard</Link>
          <h1 className="text-3xl font-bold">Standard Inventory Reports</h1>
          <p className="text-gray-500 text-sm mt-1">Generate and export granular stock ledgers, aging, and valuation reports.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Report Card 1 */}
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700 flex flex-col justify-between">
            <div>
                <h3 className="font-bold text-lg mb-2">Inventory Aging Report</h3>
                <p className="text-gray-600 dark:text-gray-400 text-sm mb-4">View stock grouped by days since last movement to identify dead stock.</p>
            </div>
            <div className="flex gap-2">
                <button className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">View Data</button>
                <a href="/api/v1/universal-reports/aging?export=csv" target="_blank" rel="noopener noreferrer">
                    <button className="bg-gray-200 text-gray-800 px-4 py-2 rounded text-sm hover:bg-gray-300">Export CSV</button>
                </a>
            </div>
        </div>

        {/* Report Card 2 */}
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700 flex flex-col justify-between">
            <div>
                <h3 className="font-bold text-lg mb-2">ABC Analysis (Pareto)</h3>
                <p className="text-gray-600 dark:text-gray-400 text-sm mb-4">Classify inventory based on consumption value over the trailing period.</p>
            </div>
            <div className="flex gap-2">
                <button className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">View Data</button>
                <a href="/api/v1/universal-reports/abc-analysis?export=csv" target="_blank" rel="noopener noreferrer">
                    <button className="bg-gray-200 text-gray-800 px-4 py-2 rounded text-sm hover:bg-gray-300">Export CSV</button>
                </a>
            </div>
        </div>

        {/* Report Card 3 */}
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700 flex flex-col justify-between">
            <div>
                <h3 className="font-bold text-lg mb-2">Stock Valuation Summary</h3>
                <p className="text-gray-600 dark:text-gray-400 text-sm mb-4">Current total on-hand quantity multiplied by unit cost per warehouse.</p>
            </div>
            <div className="flex gap-2">
                <button className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">View Data</button>
            </div>
        </div>

        {/* Report Card 4 */}
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700 flex flex-col justify-between">
            <div>
                <h3 className="font-bold text-lg mb-2">Immutable Stock Ledger</h3>
                <p className="text-gray-600 dark:text-gray-400 text-sm mb-4">Export the raw append-only ledger for financial auditing.</p>
            </div>
            <div className="flex gap-2">
                <Link href="/universal-inventory/ledger">
                    <button className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">Go to Ledger</button>
                </Link>
            </div>
        </div>

      </div>
    </div>
  );
}
