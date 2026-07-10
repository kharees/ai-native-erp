'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import apiClient from '@/lib/apiClient';

interface LedgerEntry {
  id: string;
  item_id: string;
  warehouse_id: string;
  quantity_before: number;
  movement_quantity: number;
  quantity_after: number;
  total_cost: number;
  reference_type: string;
  created_at: string;
}

const LEDGER_BASE = '/api/v1/universal-ledger/';

export default function LedgerDashboard() {
  const [entries, setEntries] = useState<LedgerEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [itemIdFilter, setItemIdFilter] = useState('');
  const [warehouseIdFilter, setWarehouseIdFilter] = useState('');
  const [referenceType, setReferenceType] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    const params: Record<string, string> = {};
    if (itemIdFilter) params.item_id = itemIdFilter;
    if (warehouseIdFilter) params.warehouse_id = warehouseIdFilter;
    if (referenceType) params.reference_type = referenceType;
    apiClient
      .get(LEDGER_BASE, { params })
      .then((res) => setEntries(res.data.items || []))
      .catch(() => setError('Failed to load ledger'))
      .finally(() => setLoading(false));
  }, [itemIdFilter, warehouseIdFilter, referenceType]);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    load();
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/universal-inventory" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Inventory Dashboard</Link>
          <h1 className="text-3xl font-bold">Universal Inventory Ledger</h1>
          <p className="text-gray-500 text-sm mt-1">Immutable stock history and valuation tracking.</p>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      <form onSubmit={handleSearch} className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow mb-6 border border-gray-200 dark:border-gray-700 flex gap-4">
        <input type="text" placeholder="Filter by Item ID..." value={itemIdFilter} onChange={(e) => setItemIdFilter(e.target.value)} className="flex-1 p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
        <input type="text" placeholder="Filter by Warehouse ID..." value={warehouseIdFilter} onChange={(e) => setWarehouseIdFilter(e.target.value)} className="flex-1 p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
        <select value={referenceType} onChange={(e) => setReferenceType(e.target.value)} className="p-2 border rounded dark:bg-gray-700 dark:border-gray-600">
          <option value="">All Reference Types</option>
          <option value="GRN">Goods Receipt Note</option>
          <option value="GI">Goods Issue</option>
          <option value="TRANSFER">Stock Transfer</option>
          <option value="ADJUST">Adjustment</option>
        </select>
        <button type="submit" className="bg-blue-600 text-white px-6 py-2 rounded shadow hover:bg-blue-700 transition-colors">Search</button>
      </form>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden border border-gray-200 dark:border-gray-700">
        <table className="min-w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
            <tr>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Date</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Item ID</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Warehouse</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Qty Before</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Movement</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Qty After</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Total Value</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {loading ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={7}>Loading ledger...</td></tr>
            ) : entries.length === 0 ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={7}>No ledger entries found.</td></tr>
            ) : entries.map((e) => (
              <tr key={e.id}>
                <td className="px-6 py-4 text-gray-500">{new Date(e.created_at).toLocaleString()}</td>
                <td className="px-6 py-4">
                  <Link href={`/universal-inventory/ledger/${e.item_id}`} className="text-blue-600 hover:underline">{e.item_id}</Link>
                </td>
                <td className="px-6 py-4 text-gray-500">{e.warehouse_id}</td>
                <td className="px-6 py-4">{e.quantity_before}</td>
                <td className="px-6 py-4 font-medium">{e.movement_quantity > 0 ? `+${e.movement_quantity}` : e.movement_quantity}</td>
                <td className="px-6 py-4">{e.quantity_after}</td>
                <td className="px-6 py-4">{Number(e.total_cost).toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
