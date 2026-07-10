'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import apiClient, { isApiError } from '@/lib/apiClient';

interface Customer {
  id: string;
  name: string;
}

interface Invoice {
  id: string;
  customer_id: string;
  invoice_number?: string;
  pi_number?: string;
  status: string;
  total_amount: number;
  _type: 'Tax' | 'Proforma';
}

const BASE = '/api/v1/omnichannel-billing/invoices';

export default function InvoicesPage() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const [customerId, setCustomerId] = useState('');
  const [invoiceNumber, setInvoiceNumber] = useState('');
  const [totalAmount, setTotalAmount] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([
      apiClient.get(`${BASE}/tax`),
      apiClient.get(`${BASE}/proforma`),
      apiClient.get('/api/v1/omnichannel-billing/customers/'),
    ])
      .then(([taxRes, proformaRes, custRes]) => {
        const tax: Invoice[] = (taxRes.data.items || []).map((i: Invoice) => ({ ...i, _type: 'Tax' as const }));
        const proforma: Invoice[] = (proformaRes.data.items || []).map((i: Invoice) => ({ ...i, _type: 'Proforma' as const }));
        setInvoices([...tax, ...proforma]);
        setCustomers(custRes.data.items || []);
      })
      .catch(() => setError('Failed to load invoices'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const customerName = (id: string) => customers.find((c) => c.id === id)?.name || id;

  const resetForm = () => {
    setShowForm(false);
    setCustomerId('');
    setInvoiceNumber('');
    setTotalAmount('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    const amount = parseFloat(totalAmount) || 0;
    try {
      await apiClient.post(`${BASE}/tax`, {
        customer_id: customerId,
        invoice_number: invoiceNumber,
        subtotal: amount,
        total_amount: amount,
      });
      resetForm();
      load();
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to create invoice');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/omnichannel-billing/analytics/dashboard" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Billing Dashboard</Link>
          <h1 className="text-2xl font-bold">Invoices Engine</h1>
          <p className="text-gray-600 dark:text-gray-400">Manage Proforma and Tax Invoices.</p>
        </div>
        <button onClick={() => (showForm ? resetForm() : setShowForm(true))} className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700 transition-colors">
          {showForm ? 'Cancel' : 'Create Invoice'}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md mb-8 border border-gray-200 dark:border-gray-700 space-y-4">
          <h2 className="text-lg font-semibold">New Tax Invoice</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Customer</label>
              <select required value={customerId} onChange={(e) => setCustomerId(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600">
                <option value="">- Select -</option>
                {customers.map((c) => (<option key={c.id} value={c.id}>{c.name}</option>))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Invoice Number</label>
              <input type="text" required value={invoiceNumber} onChange={(e) => setInvoiceNumber(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Total Amount</label>
              <input type="number" step="0.01" required value={totalAmount} onChange={(e) => setTotalAmount(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={resetForm} className="px-4 py-2 text-gray-600 hover:text-gray-900">Cancel</button>
            <button type="submit" disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Saving...' : 'Save Invoice'}
            </button>
          </div>
        </form>
      )}

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden border border-gray-200 dark:border-gray-700">
        <table className="min-w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
            <tr>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Invoice No</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Customer</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Type</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Amount</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {loading ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={5}>Loading invoices...</td></tr>
            ) : invoices.length === 0 ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={5}>No invoices found.</td></tr>
            ) : invoices.map((inv) => (
              <tr key={inv.id}>
                <td className="px-6 py-4 font-mono">{inv.invoice_number || inv.pi_number}</td>
                <td className="px-6 py-4">{customerName(inv.customer_id)}</td>
                <td className="px-6 py-4 text-gray-500">{inv._type}</td>
                <td className="px-6 py-4 font-medium">${Number(inv.total_amount).toFixed(2)}</td>
                <td className="px-6 py-4">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
                    {inv.status}
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
