'use client';

import { useState } from 'react';
import Link from 'next/link';
import apiClient, { isApiError } from '@/lib/apiClient';

export default function StandardReportsPage() {
  const [error, setError] = useState('');
  const [exporting, setExporting] = useState<string | null>(null);

  // Plain <a href> can't carry the JWT/X-Tenant-ID headers the API requires,
  // so CSV export has to go through apiClient and trigger a Blob download
  // instead of a direct browser navigation.
  const exportCsv = async (path: string, filename: string) => {
    setExporting(path);
    setError('');
    try {
      const res = await apiClient.get(path, { params: { export: 'csv' }, responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to export report');
    } finally {
      setExporting(null);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/universal-inventory/reports" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Dashboard</Link>
          <h1 className="text-3xl font-bold">Standard Inventory Reports</h1>
          <p className="text-gray-500 text-sm mt-1">Generate and export granular stock ledgers, aging, and valuation reports.</p>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700 flex flex-col justify-between">
          <div>
            <h3 className="font-bold text-lg mb-2">Inventory Aging Report</h3>
            <p className="text-gray-600 dark:text-gray-400 text-sm mb-4">View stock grouped by days since last movement to identify dead stock.</p>
          </div>
          <div className="flex gap-2">
            <Link href="/universal-inventory/reports">
              <button className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">View Data</button>
            </Link>
            <button
              onClick={() => exportCsv('/api/v1/universal-reports/aging', 'inventory_aging.csv')}
              disabled={exporting === '/api/v1/universal-reports/aging'}
              className="bg-gray-200 text-gray-800 px-4 py-2 rounded text-sm hover:bg-gray-300 disabled:opacity-50"
            >
              {exporting === '/api/v1/universal-reports/aging' ? 'Exporting...' : 'Export CSV'}
            </button>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700 flex flex-col justify-between">
          <div>
            <h3 className="font-bold text-lg mb-2">ABC Analysis (Pareto)</h3>
            <p className="text-gray-600 dark:text-gray-400 text-sm mb-4">Classify inventory based on consumption value over the trailing period.</p>
          </div>
          <div className="flex gap-2">
            <Link href="/universal-inventory/reports">
              <button className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">View Data</button>
            </Link>
            <button
              onClick={() => exportCsv('/api/v1/universal-reports/abc-analysis', 'abc_analysis.csv')}
              disabled={exporting === '/api/v1/universal-reports/abc-analysis'}
              className="bg-gray-200 text-gray-800 px-4 py-2 rounded text-sm hover:bg-gray-300 disabled:opacity-50"
            >
              {exporting === '/api/v1/universal-reports/abc-analysis' ? 'Exporting...' : 'Export CSV'}
            </button>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700 flex flex-col justify-between">
          <div>
            <h3 className="font-bold text-lg mb-2">Stock Valuation Summary</h3>
            <p className="text-gray-600 dark:text-gray-400 text-sm mb-4">Current total on-hand quantity multiplied by unit cost per warehouse.</p>
          </div>
          <div className="flex gap-2">
            <Link href="/universal-inventory/reports">
              <button className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">View Data</button>
            </Link>
          </div>
        </div>

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
