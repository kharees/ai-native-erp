'use client';

import { useEffect, useState, useCallback } from 'react';
import apiClient, { isApiError } from '@/lib/apiClient';
import { useAuthStore } from '@/store/authStore';

interface Customer {
  id: string;
  name: string;
}

interface ARLedger {
  id: string;
  customer_id: string;
  outstanding_amount: number;
  credit_limit: number;
  is_bad_debt: boolean;
}

interface ARReceipt {
  id: string;
  customer_id: string;
  receipt_number: string;
  amount: number;
  payment_mode: string;
}

const BASE = '/api/v1/finance-ar-ap';

export default function AccountsReceivablePage() {
  const tenantId = useAuthStore((s) => s.user?.tenant_id);
  const [ledgers, setLedgers] = useState<ARLedger[]>([]);
  const [receipts, setReceipts] = useState<ARReceipt[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const [customerId, setCustomerId] = useState('');
  const [receiptNumber, setReceiptNumber] = useState('');
  const [amount, setAmount] = useState('');
  const [paymentMode, setPaymentMode] = useState('CASH');

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([
      apiClient.get(`${BASE}/ar/ledgers`),
      apiClient.get(`${BASE}/ar/receipts`),
      apiClient.get('/api/v1/omnichannel-billing/customers/'),
    ])
      .then(([ledgerRes, receiptRes, custRes]) => {
        setLedgers(ledgerRes.data || []);
        setReceipts(receiptRes.data || []);
        setCustomers(custRes.data.items || []);
      })
      .catch(() => setError('Failed to load accounts receivable'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const customerName = (id: string) => customers.find((c) => c.id === id)?.name || id;

  const resetForm = () => {
    setShowForm(false);
    setCustomerId('');
    setReceiptNumber('');
    setAmount('');
    setPaymentMode('CASH');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tenantId) return;
    setSaving(true);
    setError('');
    try {
      await apiClient.post(`${BASE}/ar/receipts`, {
        tenant_id: tenantId,
        customer_id: customerId,
        receipt_number: receiptNumber,
        amount: parseFloat(amount),
        payment_mode: paymentMode,
        unallocated_amount: parseFloat(amount),
      });
      resetForm();
      load();
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to record receipt');
    } finally {
      setSaving(false);
    }
  };

  const totalOutstanding = ledgers.reduce((sum, l) => sum + Number(l.outstanding_amount), 0);
  const badDebtCount = ledgers.filter((l) => l.is_bad_debt).length;
  const totalReceipts = receipts.reduce((sum, r) => sum + Number(r.amount), 0);

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Accounts Receivable (AR)</h1>
        <button onClick={() => (showForm ? resetForm() : setShowForm(true))} className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700">
          {showForm ? 'Cancel' : 'Record Receipt'}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-white p-4 shadow rounded-lg border-l-4 border-blue-500">
          <p className="text-sm text-gray-500 font-medium">Total Outstanding</p>
          <p className="text-2xl font-bold">${totalOutstanding.toFixed(2)}</p>
        </div>
        <div className="bg-white p-4 shadow rounded-lg border-l-4 border-red-500">
          <p className="text-sm text-gray-500 font-medium">Flagged Bad Debt</p>
          <p className="text-2xl font-bold text-red-600">{badDebtCount}</p>
        </div>
        <div className="bg-white p-4 shadow rounded-lg border-l-4 border-green-500">
          <p className="text-sm text-gray-500 font-medium">Total Receipts Recorded</p>
          <p className="text-2xl font-bold">${totalReceipts.toFixed(2)}</p>
        </div>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white shadow rounded-lg p-6 mb-6 space-y-4">
          <h2 className="text-lg font-semibold">Record New Receipt</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Customer</label>
              <select required value={customerId} onChange={(e) => setCustomerId(e.target.value)} className="w-full p-2 border rounded">
                <option value="">- Select -</option>
                {customers.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Receipt Number</label>
              <input type="text" required value={receiptNumber} onChange={(e) => setReceiptNumber(e.target.value)} className="w-full p-2 border rounded" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Amount</label>
              <input type="number" step="0.01" required value={amount} onChange={(e) => setAmount(e.target.value)} className="w-full p-2 border rounded" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Payment Mode</label>
              <select value={paymentMode} onChange={(e) => setPaymentMode(e.target.value)} className="w-full p-2 border rounded">
                <option value="CASH">Cash</option>
                <option value="BANK_TRANSFER">Bank Transfer</option>
                <option value="CHEQUE">Cheque</option>
                <option value="CARD">Card</option>
              </select>
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={resetForm} className="px-4 py-2 text-gray-600 hover:text-gray-900">Cancel</button>
            <button type="submit" disabled={saving || !tenantId} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Saving...' : 'Save Receipt'}
            </button>
          </div>
        </form>
      )}

      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="px-6 py-3 bg-gray-50 border-b font-semibold text-sm">AR Ledger</div>
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Customer</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Outstanding</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Credit Limit</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {loading ? (
              <tr><td colSpan={4} className="px-6 py-4 text-center">Loading...</td></tr>
            ) : ledgers.length === 0 ? (
              <tr><td colSpan={4} className="px-6 py-4 text-center text-gray-500">No AR ledger entries found.</td></tr>
            ) : ledgers.map((item) => (
              <tr key={item.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-blue-600">{customerName(item.customer_id)}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium">${Number(item.outstanding_amount).toFixed(2)}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-500">${Number(item.credit_limit).toFixed(2)}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${item.is_bad_debt ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'}`}>
                    {item.is_bad_debt ? 'Bad Debt' : 'Active'}
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
