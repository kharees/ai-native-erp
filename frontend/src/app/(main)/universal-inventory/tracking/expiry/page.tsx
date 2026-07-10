'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import apiClient from '@/lib/apiClient';

interface Item {
  id: string;
  name: string;
}

interface Batch {
  id: string;
  item_id: string;
  batch_number: string;
  expiry_date: string | null;
}

const EXPIRY_BASE = '/api/v1/universal-tracking/expiry-alerts';
const ITEMS_BASE = '/api/v1/universal-inventory/items';

function daysUntil(dateStr: string): number {
  const diffMs = new Date(dateStr).getTime() - Date.now();
  return Math.ceil(diffMs / (1000 * 60 * 60 * 24));
}

export default function ExpiryDashboard() {
  const [batches, setBatches] = useState<Batch[]>([]);
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() + 90);
    const cutoffDate = cutoff.toISOString().slice(0, 10);

    Promise.all([
      apiClient.get(EXPIRY_BASE, { params: { cutoff_date: cutoffDate } }),
      apiClient.get(ITEMS_BASE),
    ])
      .then(([expiryRes, itemsRes]) => {
        setBatches(expiryRes.data || []);
        setItems(itemsRes.data.items || []);
      })
      .catch(() => setError('Failed to load expiry alerts'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const itemName = (id: string) => items.find((i) => i.id === id)?.name || id;

  const expired = batches.filter((b) => b.expiry_date && daysUntil(b.expiry_date) < 0);
  const within30 = batches.filter((b) => b.expiry_date && daysUntil(b.expiry_date) >= 0 && daysUntil(b.expiry_date) <= 30);
  const within90 = batches.filter((b) => b.expiry_date && daysUntil(b.expiry_date) > 30 && daysUntil(b.expiry_date) <= 90);
  const actionable = [...expired, ...within30].sort((a, b) => (a.expiry_date || '').localeCompare(b.expiry_date || ''));

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/universal-inventory" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Inventory Dashboard</Link>
          <h1 className="text-3xl font-bold text-red-600">Expiry Management & Alerts</h1>
          <p className="text-gray-500 text-sm mt-1">Monitor near-expiry stock and enforce FEFO (First-Expired-First-Out) picking.</p>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
          <h3 className="text-red-800 dark:text-red-400 font-semibold mb-2">Expired Stock</h3>
          <p className="text-3xl font-bold text-red-600">{loading ? '-' : expired.length}</p>
          <p className="text-sm text-red-600 mt-2">Requires immediate quarantine.</p>
        </div>
        <div className="bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg p-6">
          <h3 className="text-orange-800 dark:text-orange-400 font-semibold mb-2">Expiring within 30 Days</h3>
          <p className="text-3xl font-bold text-orange-600">{loading ? '-' : within30.length}</p>
          <p className="text-sm text-orange-600 mt-2">Prioritize for FEFO picking.</p>
        </div>
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-6">
          <h3 className="text-yellow-800 dark:text-yellow-400 font-semibold mb-2">Expiring within 90 Days</h3>
          <p className="text-3xl font-bold text-yellow-600">{loading ? '-' : within90.length}</p>
          <p className="text-sm text-yellow-600 mt-2">Monitor turnover rate.</p>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden border border-gray-200 dark:border-gray-700">
        <div className="p-4 border-b dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
          <h3 className="font-semibold text-red-600">Action Required: Approaching Expiry</h3>
        </div>
        <table className="min-w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
            <tr>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Batch Number</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Item</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Expiry Date</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Days Remaining</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {loading ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={4}>Loading...</td></tr>
            ) : actionable.length === 0 ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={4}>All stock is healthy.</td></tr>
            ) : actionable.map((b) => {
              const days = b.expiry_date ? daysUntil(b.expiry_date) : null;
              return (
                <tr key={b.id}>
                  <td className="px-6 py-4 font-mono">{b.batch_number}</td>
                  <td className="px-6 py-4">{itemName(b.item_id)}</td>
                  <td className="px-6 py-4 text-gray-500">{b.expiry_date}</td>
                  <td className={`px-6 py-4 font-medium ${days !== null && days < 0 ? 'text-red-600' : 'text-orange-600'}`}>
                    {days !== null && days < 0 ? `Expired ${Math.abs(days)}d ago` : `${days}d`}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
