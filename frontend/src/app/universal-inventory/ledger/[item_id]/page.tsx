import Link from 'next/link';

export default function ItemTimelinePage({ params }: { params: { item_id: string } }) {
  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/universal-inventory/ledger" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Master Ledger</Link>
          <h1 className="text-3xl font-bold">Item Stock Timeline</h1>
          <p className="text-gray-500 text-sm mt-1">Traceability for Item: {params.item_id}</p>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden border border-gray-200 dark:border-gray-700">
        <div className="p-4 border-b dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
            <h3 className="font-semibold">Chronological Movement History</h3>
        </div>
        <table className="min-w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
            <tr>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Date</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Warehouse</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Reference</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Qty Before</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Movement</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Qty After</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            <tr>
              <td className="px-6 py-4 text-center text-gray-500" colSpan={6}>No history found for this item.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
