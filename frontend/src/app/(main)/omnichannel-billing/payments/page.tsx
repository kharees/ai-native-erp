'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import apiClient, { isApiError } from '@/lib/apiClient';

interface Customer {
  id: string;
  name: string;
}

interface Refund {
  id: string;
  customer_id: string;
  refund_number: string;
  payment_mode: string;
  amount_refunded: number;
  status: string;
}

const BASE = '/api/v1/omnichannel-billing/payments';

export default function PaymentsPage() {
  const [refunds, setRefunds] = useState<Refund[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const [customerId, setCustomerId] = useState('');
  const [refundNumber, setRefundNumber] = useState('');
  const [paymentMode, setPaymentMode] = useState('BANK_TRANSFER');
  const [amount, setAmount] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([apiClient.get(`${BASE}/refunds`), apiClient.get('/api/v1/omnichannel-billing/customers/')])
      .then(([refundRes, custRes]) => {
        setRefunds(refundRes.data.items || []);
        setCustomers(custRes.data.items || []);
      })
      .catch(() => setError('Failed to load refunds'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const customerName = (id: string) => customers.find((c) => c.id === id)?.name || id;

  const resetForm = () => {
    setShowForm(false);
    setCustomerId('');
    setRefundNumber('');
    setPaymentMode('BANK_TRANSFER');
    setAmount('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      await apiClient.post(`${BASE}/refunds`, {
        customer_id: customerId,
        refund_number: refundNumber,
        payment_mode: paymentMode,
        amount_refunded: parseFloat(amount) || 0,
      });
      resetForm();
      load();
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to initiate refund');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/omnichannel-billing/analytics/dashboard" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Billing Dashboard</Link>
          <h1 className="text-2xl font-bold">Payments Engine</h1>
          <p className="text-gray-600 dark:text-gray-400">Process refunds and allocations.</p>
        </div>
        <button onClick={() => (showForm ? resetForm() : setShowForm(true))} className="bg-red-600 text-white px-4 py-2 rounded shadow hover:bg-red-700 transition-colors">
          {showForm ? 'Cancel' : 'Initiate Refund'}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md mb-8 border border-gray-200 dark:border-gray-700 space-y-4">
          <h2 className="text-lg font-semibold">Initiate Refund</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Customer</label>
              <select required value={customerId} onChange={(e) => setCustomerId(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600">
                <option value="">- Select -</option>
                {customers.map((c) => (<option key={c.id} value={c.id}>{c.name}</option>))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Refund Number</label>
              <input type="text" required value={refundNumber} onChange={(e) => setRefundNumber(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Mode</label>
              <select value={paymentMode} onChange={(e) => setPaymentMode(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600">
                <option value="BANK_TRANSFER">Bank Transfer</option>
                <option value="CASH">Cash</option>
                <option value="CHEQUE">Cheque</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Amount</label>
              <input type="number" step="0.01" required value={amount} onChange={(e) => setAmount(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={resetForm} className="px-4 py-2 text-gray-600 hover:text-gray-900">Cancel</button>
            <button type="submit" disabled={saving} className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50">
              {saving ? 'Processing...' : 'Save Refund'}
            </button>
          </div>
        </form>
      )}

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden border border-gray-200 dark:border-gray-700">
        <h2 className="p-4 font-semibold border-b dark:border-gray-700">Refund History</h2>
        <table className="min-w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
            <tr>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Refund No</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Customer</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Mode</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Amount</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {loading ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={5}>Loading refunds...</td></tr>
            ) : refunds.length === 0 ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={5}>No pending refunds.</td></tr>
            ) : refunds.map((r) => (
              <tr key={r.id}>
                <td className="px-6 py-4 font-mono">{r.refund_number}</td>
                <td className="px-6 py-4">{customerName(r.customer_id)}</td>
                <td className="px-6 py-4 text-gray-500">{r.payment_mode}</td>
                <td className="px-6 py-4 font-medium">${Number(r.amount_refunded).toFixed(2)}</td>
                <td className="px-6 py-4">{r.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
