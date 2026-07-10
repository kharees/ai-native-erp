'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import apiClient from '@/lib/apiClient';

interface Serial {
  id: string;
  serial_number: string;
  item_id: string;
  status: string;
  warehouse_id: string | null;
  warranty_expiry: string | null;
}

const SERIALS_BASE = '/api/v1/universal-tracking/serials';

export default function SerialsDashboard() {
  const [serials, setSerials] = useState<Serial[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [serialSearch, setSerialSearch] = useState('');
  const [itemIdFilter, setItemIdFilter] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    const params: Record<string, string> = {};
    if (serialSearch) params.serial_number = serialSearch;
    if (itemIdFilter) params.item_id = itemIdFilter;
    apiClient
      .get(SERIALS_BASE, { params })
      .then((res) => setSerials(res.data.items || []))
      .catch(() => setError('Failed to load serials'))
      .finally(() => setLoading(false));
  }, [serialSearch, itemIdFilter]);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleTrace = (e: React.FormEvent) => {
    e.preventDefault();
    load();
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/universal-inventory" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Inventory Dashboard</Link>
          <h1 className="text-3xl font-bold">Serial Number Tracking</h1>
          <p className="text-gray-500 text-sm mt-1">Trace individual unit histories, warranties, and exact locations.</p>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      <form onSubmit={handleTrace} className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow mb-6 border border-gray-200 dark:border-gray-700 flex gap-4">
        <input type="text" placeholder="Search Serial Number..." value={serialSearch} onChange={(e) => setSerialSearch(e.target.value)} className="flex-1 p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
        <input type="text" placeholder="Filter by Item ID..." value={itemIdFilter} onChange={(e) => setItemIdFilter(e.target.value)} className="flex-1 p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
        <button type="submit" className="bg-blue-600 text-white px-6 py-2 rounded shadow hover:bg-blue-700 transition-colors">Trace</button>
      </form>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden border border-gray-200 dark:border-gray-700">
        <table className="min-w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
            <tr>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Serial Number</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Item ID</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Status</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Current Warehouse</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Warranty Expiry</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {loading ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={5}>Loading serials...</td></tr>
            ) : serials.length === 0 ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={5}>No serials found.</td></tr>
            ) : serials.map((s) => (
              <tr key={s.id}>
                <td className="px-6 py-4 font-mono">{s.serial_number}</td>
                <td className="px-6 py-4 text-gray-500">{s.item_id}</td>
                <td className="px-6 py-4">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                    {s.status}
                  </span>
                </td>
                <td className="px-6 py-4 text-gray-500">{s.warehouse_id || '-'}</td>
                <td className="px-6 py-4 text-gray-500">{s.warranty_expiry || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
