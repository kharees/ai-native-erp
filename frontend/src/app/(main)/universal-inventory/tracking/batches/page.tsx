'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import apiClient, { isApiError } from '@/lib/apiClient';

interface Item {
  id: string;
  name: string;
}

interface Batch {
  id: string;
  item_id: string;
  batch_number: string;
  mfg_date: string | null;
  expiry_date: string | null;
  status: string;
}

const BATCHES_BASE = '/api/v1/universal-tracking/batches';
const ITEMS_BASE = '/api/v1/universal-inventory/items';

export default function BatchesDashboard() {
  const [batches, setBatches] = useState<Batch[]>([]);
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const [itemId, setItemId] = useState('');
  const [batchNumber, setBatchNumber] = useState('');
  const [mfgDate, setMfgDate] = useState('');
  const [expiryDate, setExpiryDate] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([apiClient.get(BATCHES_BASE), apiClient.get(ITEMS_BASE)])
      .then(([batchRes, itemsRes]) => {
        setBatches(batchRes.data.items || []);
        setItems(itemsRes.data.items || []);
      })
      .catch(() => setError('Failed to load batches'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const itemName = (id: string) => items.find((i) => i.id === id)?.name || id;

  const resetForm = () => {
    setShowForm(false);
    setItemId('');
    setBatchNumber('');
    setMfgDate('');
    setExpiryDate('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      await apiClient.post(BATCHES_BASE, {
        item_id: itemId,
        batch_number: batchNumber,
        mfg_date: mfgDate || null,
        expiry_date: expiryDate || null,
      });
      resetForm();
      load();
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to create batch');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/universal-inventory" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Inventory Dashboard</Link>
          <h1 className="text-3xl font-bold">Batch Master Management</h1>
          <p className="text-gray-500 text-sm mt-1">Manage manufacturing lots, expiry dates, and batch traceability.</p>
        </div>
        <div className="space-x-2">
          <button onClick={() => (showForm ? resetForm() : setShowForm(true))} className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700 transition-colors">
            {showForm ? 'Cancel' : 'Create Batch'}
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md border border-gray-200 dark:border-gray-700 space-y-4">
          <h2 className="text-lg font-semibold">Create New Batch</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Item</label>
              <select required value={itemId} onChange={(e) => setItemId(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600">
                <option value="">Select Item...</option>
                {items.map((i) => (
                  <option key={i.id} value={i.id}>{i.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Batch Number</label>
              <input type="text" required value={batchNumber} onChange={(e) => setBatchNumber(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Mfg Date</label>
              <input type="date" value={mfgDate} onChange={(e) => setMfgDate(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Expiry Date</label>
              <input type="date" value={expiryDate} onChange={(e) => setExpiryDate(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={resetForm} className="px-4 py-2 text-gray-600 hover:text-gray-900">Cancel</button>
            <button type="submit" disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Saving...' : 'Save Batch'}
            </button>
          </div>
        </form>
      )}

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden border border-gray-200 dark:border-gray-700">
        <table className="min-w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
            <tr>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Batch Number</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Item</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Mfg Date</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Expiry Date</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {loading ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={5}>Loading batches...</td></tr>
            ) : batches.length === 0 ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={5}>No batches registered.</td></tr>
            ) : batches.map((b) => (
              <tr key={b.id}>
                <td className="px-6 py-4 font-mono">{b.batch_number}</td>
                <td className="px-6 py-4">{itemName(b.item_id)}</td>
                <td className="px-6 py-4 text-gray-500">{b.mfg_date || '-'}</td>
                <td className="px-6 py-4 text-gray-500">{b.expiry_date || '-'}</td>
                <td className="px-6 py-4">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                    {b.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
