'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import apiClient, { isApiError } from '@/lib/apiClient';

interface Customer {
  id: string;
  name: string;
}

interface Item {
  id: string;
  name: string;
}

interface Challan {
  id: string;
  customer_id: string;
  challan_number: string;
  status: string;
  dispatch_date: string | null;
}

const BASE = '/api/v1/omnichannel-billing/documents';

export default function FulfillmentPage() {
  const [challans, setChallans] = useState<Challan[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const [customerId, setCustomerId] = useState('');
  const [challanNumber, setChallanNumber] = useState('');
  const [itemId, setItemId] = useState('');
  const [quantity, setQuantity] = useState('1');

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([
      apiClient.get(`${BASE}/delivery-challans`),
      apiClient.get('/api/v1/omnichannel-billing/customers/'),
      apiClient.get('/api/v1/universal-inventory/items'),
    ])
      .then(([challanRes, custRes, itemRes]) => {
        setChallans(challanRes.data.items || []);
        setCustomers(custRes.data.items || []);
        setItems(itemRes.data.items || []);
      })
      .catch(() => setError('Failed to load fulfillment documents'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const customerName = (id: string) => customers.find((c) => c.id === id)?.name || id;

  const resetForm = () => {
    setShowForm(false);
    setCustomerId('');
    setChallanNumber('');
    setItemId('');
    setQuantity('1');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      await apiClient.post(`${BASE}/delivery-challans`, {
        customer_id: customerId,
        challan_number: challanNumber,
        items: [{ item_id: itemId, quantity_dispatched: parseFloat(quantity) }],
      });
      resetForm();
      load();
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to create delivery challan');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/omnichannel-billing/analytics/dashboard" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Billing Dashboard</Link>
          <h1 className="text-2xl font-bold">Fulfillment Engine</h1>
          <p className="text-gray-600 dark:text-gray-400">Manage Delivery Challans.</p>
        </div>
        <button onClick={() => (showForm ? resetForm() : setShowForm(true))} className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700 transition-colors">
          {showForm ? 'Cancel' : 'Create Document'}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md mb-8 border border-gray-200 dark:border-gray-700 space-y-4">
          <h2 className="text-lg font-semibold">New Delivery Challan</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Customer</label>
              <select required value={customerId} onChange={(e) => setCustomerId(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600">
                <option value="">- Select -</option>
                {customers.map((c) => (<option key={c.id} value={c.id}>{c.name}</option>))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Challan Number</label>
              <input type="text" required value={challanNumber} onChange={(e) => setChallanNumber(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Item</label>
              <select required value={itemId} onChange={(e) => setItemId(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600">
                <option value="">- Select -</option>
                {items.map((i) => (<option key={i.id} value={i.id}>{i.name}</option>))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Quantity</label>
              <input type="number" step="0.01" required value={quantity} onChange={(e) => setQuantity(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={resetForm} className="px-4 py-2 text-gray-600 hover:text-gray-900">Cancel</button>
            <button type="submit" disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Saving...' : 'Save Challan'}
            </button>
          </div>
        </form>
      )}

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden border border-gray-200 dark:border-gray-700">
        <table className="min-w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
            <tr>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Document No</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Customer</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Dispatch Date</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {loading ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={4}>Loading fulfillment documents...</td></tr>
            ) : challans.length === 0 ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={4}>No fulfillment documents found.</td></tr>
            ) : challans.map((c) => (
              <tr key={c.id}>
                <td className="px-6 py-4 font-mono">{c.challan_number}</td>
                <td className="px-6 py-4">{customerName(c.customer_id)}</td>
                <td className="px-6 py-4 text-gray-500">{c.dispatch_date ? new Date(c.dispatch_date).toLocaleDateString() : '-'}</td>
                <td className="px-6 py-4">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
                    {c.status}
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
