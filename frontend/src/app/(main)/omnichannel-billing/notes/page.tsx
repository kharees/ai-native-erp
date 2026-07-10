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

interface Note {
  id: string;
  customer_id: string;
  note_number: string;
  status: string;
  total_amount: number;
  _type: 'Credit' | 'Debit';
}

const BASE = '/api/v1/omnichannel-billing/returns';

export default function NotesPage() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const [noteType, setNoteType] = useState<'credit' | 'debit'>('credit');
  const [customerId, setCustomerId] = useState('');
  const [noteNumber, setNoteNumber] = useState('');
  const [itemId, setItemId] = useState('');
  const [quantity, setQuantity] = useState('1');
  const [unitPrice, setUnitPrice] = useState('');
  const [reason, setReason] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([
      apiClient.get(`${BASE}/credit-notes`),
      apiClient.get(`${BASE}/debit-notes`),
      apiClient.get('/api/v1/omnichannel-billing/customers/'),
      apiClient.get('/api/v1/universal-inventory/items'),
    ])
      .then(([creditRes, debitRes, custRes, itemRes]) => {
        const credit: Note[] = (creditRes.data.items || []).map((n: Note) => ({ ...n, _type: 'Credit' as const }));
        const debit: Note[] = (debitRes.data.items || []).map((n: Note) => ({ ...n, _type: 'Debit' as const }));
        setNotes([...credit, ...debit]);
        setCustomers(custRes.data.items || []);
        setItems(itemRes.data.items || []);
      })
      .catch(() => setError('Failed to load notes'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const customerName = (id: string) => customers.find((c) => c.id === id)?.name || id;

  const resetForm = () => {
    setShowForm(false);
    setCustomerId('');
    setNoteNumber('');
    setItemId('');
    setQuantity('1');
    setUnitPrice('');
    setReason('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    const qty = parseFloat(quantity);
    const price = parseFloat(unitPrice);
    const lineTotal = qty * price;
    try {
      await apiClient.post(`${BASE}/${noteType}-notes`, {
        customer_id: customerId,
        note_number: noteNumber,
        reason: reason || null,
        total_amount: lineTotal,
        items: [{ item_id: itemId, quantity: qty, unit_price: price, line_total: lineTotal }],
      });
      resetForm();
      load();
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to issue note');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/omnichannel-billing/analytics/dashboard" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Billing Dashboard</Link>
          <h1 className="text-2xl font-bold">Credit & Debit Notes</h1>
          <p className="text-gray-600 dark:text-gray-400">Manage financial adjustments and returns.</p>
        </div>
        <button onClick={() => (showForm ? resetForm() : setShowForm(true))} className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700 transition-colors">
          {showForm ? 'Cancel' : 'Issue Note'}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md mb-8 border border-gray-200 dark:border-gray-700 space-y-4">
          <h2 className="text-lg font-semibold">Issue New Note</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Type</label>
              <select value={noteType} onChange={(e) => setNoteType(e.target.value as 'credit' | 'debit')} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600">
                <option value="credit">Credit Note</option>
                <option value="debit">Debit Note</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Customer</label>
              <select required value={customerId} onChange={(e) => setCustomerId(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600">
                <option value="">- Select -</option>
                {customers.map((c) => (<option key={c.id} value={c.id}>{c.name}</option>))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Note Number</label>
              <input type="text" required value={noteNumber} onChange={(e) => setNoteNumber(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
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
            <div>
              <label className="block text-sm font-medium mb-1">Unit Price</label>
              <input type="number" step="0.01" required value={unitPrice} onChange={(e) => setUnitPrice(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Reason</label>
            <input type="text" value={reason} onChange={(e) => setReason(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={resetForm} className="px-4 py-2 text-gray-600 hover:text-gray-900">Cancel</button>
            <button type="submit" disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Saving...' : 'Save Note'}
            </button>
          </div>
        </form>
      )}

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden border border-gray-200 dark:border-gray-700">
        <table className="min-w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
            <tr>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Note No</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Type</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Customer</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Amount</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {loading ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={5}>Loading notes...</td></tr>
            ) : notes.length === 0 ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={5}>No credit or debit notes found.</td></tr>
            ) : notes.map((n) => (
              <tr key={n.id}>
                <td className="px-6 py-4 font-mono">{n.note_number}</td>
                <td className="px-6 py-4 text-gray-500">{n._type}</td>
                <td className="px-6 py-4">{customerName(n.customer_id)}</td>
                <td className="px-6 py-4 font-medium">${Number(n.total_amount).toFixed(2)}</td>
                <td className="px-6 py-4">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
                    {n.status}
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
