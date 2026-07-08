import Link from 'next/link';

export default function POSPage() {
  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900 flex flex-col">
      <header className="bg-blue-600 text-white p-4 flex justify-between items-center shadow-md">
        <div>
          <Link href="/omnichannel-billing" className="hover:underline text-sm opacity-80">&larr; Dashboard</Link>
          <h1 className="text-xl font-bold">POS Terminal - Universal Billing</h1>
        </div>
        <div className="flex space-x-4">
          <button className="bg-blue-500 hover:bg-blue-700 px-3 py-1 rounded">Hold Bill</button>
          <button className="bg-blue-500 hover:bg-blue-700 px-3 py-1 rounded">Resume Bill</button>
          <button className="bg-red-500 hover:bg-red-700 px-3 py-1 rounded font-bold">End Shift</button>
        </div>
      </header>
      
      <main className="flex-1 flex p-4 space-x-4">
        {/* Product Grid / Scanner */}
        <div className="w-2/3 bg-white dark:bg-gray-800 rounded-lg shadow p-4 border border-gray-200 dark:border-gray-700 flex flex-col">
          <input type="text" placeholder="Scan Barcode / QR Code..." className="w-full p-3 border rounded mb-4 text-lg bg-gray-50 dark:bg-gray-900 dark:text-white" />
          <div className="flex-1 flex items-center justify-center text-gray-400">
            [Product Grid Component]
          </div>
        </div>

        {/* Cart View */}
        <div className="w-1/3 bg-white dark:bg-gray-800 rounded-lg shadow p-4 border border-gray-200 dark:border-gray-700 flex flex-col">
          <h2 className="text-lg font-bold mb-4 border-b pb-2">Current Cart</h2>
          <div className="flex-1 overflow-y-auto mb-4">
            <p className="text-gray-500 text-center mt-10">Cart is empty.</p>
          </div>
          <div className="border-t pt-4">
            <div className="flex justify-between font-bold text-xl mb-4">
              <span>Total:</span>
              <span>₹0.00</span>
            </div>
            <button className="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-3 rounded text-xl shadow-lg transition-colors">
              FAST CHECKOUT
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
