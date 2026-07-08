import Link from 'next/link';

export default function AICopilotPage() {
  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/omnichannel-billing" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Billing Dashboard</Link>
          <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-500 to-purple-600">
            AI Billing Copilot
          </h1>
          <p className="text-gray-600 dark:text-gray-400">Advisory intelligence for risk, fraud, and smart drafting.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 relative overflow-hidden">
          <div className="absolute top-0 left-0 w-1 h-full bg-red-500"></div>
          <h3 className="text-lg font-bold mb-2">Fraud Detection Alerts</h3>
          <p className="text-sm text-gray-500 mb-4">No active anomalies detected in current billing cycles.</p>
          <button className="bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-white px-4 py-2 rounded text-sm hover:bg-gray-200 transition-colors">
            Run Manual Scan
          </button>
        </div>
        
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 relative overflow-hidden">
          <div className="absolute top-0 left-0 w-1 h-full bg-purple-500"></div>
          <h3 className="text-lg font-bold mb-2">Smart Invoice Drafts</h3>
          <p className="text-sm text-gray-500 mb-4">AI suggests missing HSN codes and loyalty discounts automatically during checkout.</p>
          <button className="bg-purple-600 text-white px-4 py-2 rounded text-sm hover:bg-purple-700 transition-colors shadow">
            Configure Drafting Rules
          </button>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-8 border border-gray-200 dark:border-gray-700">
         <h2 className="text-xl font-bold mb-4">Natural Language Search</h2>
         <input 
            type="text" 
            placeholder="e.g., 'Show me all overdue invoices for Acme Corp last month...'" 
            className="w-full p-4 text-lg border border-gray-300 dark:border-gray-600 rounded shadow-inner bg-gray-50 dark:bg-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
         />
         <div className="mt-6 text-center text-gray-400">
             Ready to assist.
         </div>
      </div>
    </div>
  );
}
