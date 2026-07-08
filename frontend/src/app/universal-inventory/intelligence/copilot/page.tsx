import Link from 'next/link';

export default function CopilotPage() {
  return (
    <div className="p-8 max-w-4xl mx-auto h-[calc(100vh-4rem)] flex flex-col">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/universal-inventory/intelligence" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to AI Dashboard</Link>
          <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-purple-600 to-blue-600">Inventory AI Copilot</h1>
          <p className="text-gray-500 text-sm mt-1">Ask questions about your stock, forecasts, and risks.</p>
        </div>
      </div>

      <div className="flex-1 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 flex flex-col overflow-hidden">
          
          {/* Chat History */}
          <div className="flex-1 p-6 overflow-y-auto bg-gray-50 dark:bg-gray-900/50 space-y-6">
              
              {/* Bot Welcome Message */}
              <div className="flex gap-4">
                  <div className="w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center text-white font-bold shrink-0">
                      AI
                  </div>
                  <div className="bg-white dark:bg-gray-800 p-4 rounded-lg rounded-tl-none border border-gray-200 dark:border-gray-700 shadow-sm max-w-[80%]">
                      <p className="text-sm">Hello! I am your Universal Inventory AI Copilot. I can help you forecast demand, optimize safety stock, or identify risky inventory. What would you like to explore?</p>
                      <div className="mt-4 flex flex-wrap gap-2">
                          <span className="text-xs bg-gray-100 dark:bg-gray-700 px-3 py-1 rounded-full cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-600">"Show low stock items"</span>
                          <span className="text-xs bg-gray-100 dark:bg-gray-700 px-3 py-1 rounded-full cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-600">"Show dead stock"</span>
                          <span className="text-xs bg-gray-100 dark:bg-gray-700 px-3 py-1 rounded-full cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-600">"What products should I reorder?"</span>
                      </div>
                  </div>
              </div>

              {/* User Message Example */}
              <div className="flex gap-4 flex-row-reverse">
                  <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold shrink-0">
                      U
                  </div>
                  <div className="bg-blue-600 text-white p-4 rounded-lg rounded-tr-none shadow-sm max-w-[80%]">
                      <p className="text-sm">Which items will expire next month?</p>
                  </div>
              </div>

              {/* Bot Response Example */}
              <div className="flex gap-4">
                  <div className="w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center text-white font-bold shrink-0">
                      AI
                  </div>
                  <div className="bg-white dark:bg-gray-800 p-4 rounded-lg rounded-tl-none border border-gray-200 dark:border-gray-700 shadow-sm max-w-[80%]">
                      <p className="text-sm">You have 3 batches expiring within the next 30 days. I recommend prioritizing them for FEFO picking immediately.</p>
                      <button className="mt-3 text-xs bg-purple-100 text-purple-700 px-3 py-1.5 rounded hover:bg-purple-200 border border-purple-200 font-medium">
                          View Expiring Batches &rarr;
                      </button>
                  </div>
              </div>

          </div>

          {/* Input Area */}
          <div className="p-4 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
              <div className="flex gap-2">
                  <input 
                    type="text" 
                    placeholder="Ask about your inventory..." 
                    className="flex-1 p-3 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                  <button className="bg-purple-600 text-white px-6 py-3 rounded-lg shadow hover:bg-purple-700 transition-colors font-semibold">
                      Send
                  </button>
              </div>
              <p className="text-xs text-gray-400 mt-2 text-center">AI recommendations are advisory only. Human approval is required for all stock movements.</p>
          </div>

      </div>
    </div>
  );
}
