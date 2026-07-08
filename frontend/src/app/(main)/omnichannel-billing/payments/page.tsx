import Link from 'next/link';

export default function PaymentsPage() {
  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/omnichannel-billing" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Billing Dashboard</Link>
          <h1 className="text-2xl font-bold">Payments Engine</h1>
          <p className="text-gray-600 dark:text-gray-400">Process refunds and allocations.</p>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 border border-gray-200 dark:border-gray-700">
        <h2 className="text-lg font-semibold mb-4">Refund Processing</h2>
        <p className="text-sm text-gray-500 mb-4">No pending refunds.</p>
        <button className="bg-red-600 text-white px-4 py-2 rounded shadow hover:bg-red-700 transition-colors">
          Initiate Refund
        </button>
      </div>
    </div>
  );
}
