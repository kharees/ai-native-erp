'use client';
import { useState } from 'react';

export default function ItemMasterPage() {
  const [showForm, setShowForm] = useState(false);
  
  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Universal Item Master</h1>
        <button onClick={() => setShowForm(!showForm)} className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700 transition-colors">
          {showForm ? 'Cancel' : 'Create Item'}
        </button>
      </div>

      {showForm ? (
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md mb-8 border border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold mb-4">Create New Universal Item</h2>
          <form className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Item Code</label>
                <input type="text" className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">SKU</label>
                <input type="text" className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Item Name</label>
                <input type="text" className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Status</label>
                <select className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600">
                  <option>draft</option>
                  <option>active</option>
                  <option>inactive</option>
                </select>
              </div>
            </div>
            
            <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
              <h3 className="text-md font-medium mb-2">Dynamic JSONB Attributes Engine</h3>
              <p className="text-xs text-gray-500 mb-4">Add infinite custom metadata fields without schema changes.</p>
              
              <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 flex gap-2">
                 <input type="text" placeholder="Attribute Key (e.g. Voltage, GSM, Material)" className="flex-1 p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
                 <input type="text" placeholder="Value (e.g. 220V, 400g, Steel)" className="flex-1 p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
                 <button type="button" className="bg-gray-200 dark:bg-gray-700 px-4 py-2 rounded text-sm hover:bg-gray-300 transition-colors">Add</button>
              </div>
            </div>

            <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
              <h3 className="text-md font-medium mb-2">Variant Engine Configuration</h3>
              <p className="text-xs text-gray-500 mb-4">Define metadata-driven variant properties for parent-child relationship tracking.</p>
              
              <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 flex gap-2">
                 <input type="text" placeholder="Variant Dimension (e.g. Size, Color)" className="flex-1 p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
                 <input type="text" placeholder="Values (e.g. S, M, L)" className="flex-1 p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
                 <button type="button" className="bg-gray-200 dark:bg-gray-700 px-4 py-2 rounded text-sm hover:bg-gray-300 transition-colors">Add Rule</button>
              </div>
            </div>
            
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 text-gray-600 hover:text-gray-900">Cancel</button>
              <button type="button" className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">Save Item</button>
            </div>
          </form>
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden border border-gray-200 dark:border-gray-700">
          <table className="min-w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
              <tr>
                <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">SKU</th>
                <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Item Name</th>
                <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Status</th>
                <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Dynamic Attributes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              <tr>
                <td className="px-6 py-4 text-center text-gray-500" colSpan={4}>No items found. Create one to begin.</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
