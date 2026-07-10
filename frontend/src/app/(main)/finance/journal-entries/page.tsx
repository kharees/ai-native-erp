'use client';

import { useEffect, useState, useCallback } from 'react';
import apiClient, { isApiError } from '@/lib/apiClient';
import { useAuthStore } from '@/store/authStore';

interface Account {
  id: string;
  account_code: string;
  name: string;
}

interface Voucher {
  id: string;
  voucher_number: string;
  entry_date: string;
  reference: string | null;
  status: string;
  total_debit: number;
}

const JOURNALS_BASE = '/api/v1/finance-core/journal-vouchers';
const JOURNALS_LIST = '/api/v1/finance-core/journals';
const ACCOUNTS_BASE = '/api/v1/finance-core/accounts';

export default function JournalEntriesPage() {
  const tenantId = useAuthStore((s) => s.user?.tenant_id);
  const [vouchers, setVouchers] = useState<Voucher[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const [voucherNumber, setVoucherNumber] = useState('');
  const [reference, setReference] = useState('');
  const [debitAccountId, setDebitAccountId] = useState('');
  const [creditAccountId, setCreditAccountId] = useState('');
  const [amount, setAmount] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([apiClient.get(JOURNALS_LIST), apiClient.get(ACCOUNTS_BASE)])
      .then(([voucherRes, accountRes]) => {
        setVouchers(voucherRes.data || []);
        setAccounts(accountRes.data || []);
      })
      .catch(() => setError('Failed to load journal entries'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const resetForm = () => {
    setShowForm(false);
    setVoucherNumber('');
    setReference('');
    setDebitAccountId('');
    setCreditAccountId('');
    setAmount('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tenantId) return;
    setSaving(true);
    setError('');
    const amt = parseFloat(amount) || 0;
    try {
      await apiClient.post(JOURNALS_BASE, {
        tenant_id: tenantId,
        voucher_number: voucherNumber,
        reference: reference || null,
        entry_date: new Date().toISOString(),
        lines: [
          { account_id: debitAccountId, debit: amt, credit: 0 },
          { account_id: creditAccountId, debit: 0, credit: amt },
        ],
      });
      resetForm();
      load();
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to create journal voucher');
    } finally {
      setSaving(false);
    }
  };

  const handleApprove = async (id: string) => {
    setError('');
    try {
      await apiClient.post(`${JOURNALS_LIST}/${id}/approve`);
      load();
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to approve voucher');
    }
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Journal Entries</h1>
        <button onClick={() => (showForm ? resetForm() : setShowForm(true))} className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700">
          {showForm ? 'Cancel' : '+ Create Journal Entry'}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white shadow rounded-lg p-6 mb-6 space-y-4">
          <h2 className="text-lg font-semibold">New Journal Voucher (Simple Double-Entry)</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Voucher Number</label>
              <input type="text" required value={voucherNumber} onChange={(e) => setVoucherNumber(e.target.value)} className="w-full p-2 border rounded" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Reference</label>
              <input type="text" value={reference} onChange={(e) => setReference(e.target.value)} className="w-full p-2 border rounded" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Amount</label>
              <input type="number" step="0.01" required value={amount} onChange={(e) => setAmount(e.target.value)} className="w-full p-2 border rounded" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Debit Account</label>
              <select required value={debitAccountId} onChange={(e) => setDebitAccountId(e.target.value)} className="w-full p-2 border rounded">
                <option value="">- Select -</option>
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>{a.account_code} - {a.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Credit Account</label>
              <select required value={creditAccountId} onChange={(e) => setCreditAccountId(e.target.value)} className="w-full p-2 border rounded">
                <option value="">- Select -</option>
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>{a.account_code} - {a.name}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={resetForm} className="px-4 py-2 text-gray-600 hover:text-gray-900">Cancel</button>
            <button type="submit" disabled={saving || !tenantId} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Saving...' : 'Post Voucher'}
            </button>
          </div>
        </form>
      )}

      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Voucher #</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Reference</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Total Amount</th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {loading ? (
              <tr><td colSpan={6} className="px-6 py-4 text-center">Loading journal vouchers...</td></tr>
            ) : vouchers.length === 0 ? (
              <tr><td colSpan={6} className="px-6 py-4 text-center text-gray-500">No journal vouchers found.</td></tr>
            ) : vouchers.map((voucher) => (
              <tr key={voucher.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-blue-600">{voucher.voucher_number}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{new Date(voucher.entry_date).toLocaleDateString()}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{voucher.reference || '-'}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                    voucher.status === 'posted' ? 'bg-green-100 text-green-800' :
                    voucher.status === 'draft' ? 'bg-gray-100 text-gray-800' :
                    'bg-yellow-100 text-yellow-800'
                  }`}>
                    {voucher.status}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium text-gray-900">
                  ${Number(voucher.total_debit).toFixed(2)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                  {voucher.status !== 'posted' && (
                    <button onClick={() => handleApprove(voucher.id)} className="text-green-600 hover:text-green-900">Approve</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
