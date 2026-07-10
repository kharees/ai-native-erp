'use client';

import { useEffect, useState, useCallback } from 'react';
import apiClient, { isApiError } from '@/lib/apiClient';
import { useAuthStore } from '@/store/authStore';

interface BankAccount {
  id: string;
  bank_name: string;
  account_number: string;
  current_balance: number;
}

interface CashAccount {
  id: string;
  name: string;
  is_petty_cash: boolean;
  balance: number;
}

const BANK_ACCOUNTS_BASE = '/api/v1/omnichannel-billing/banks/accounts';
const CASH_ACCOUNTS_BASE = '/api/v1/finance-ar-ap/cash-accounts';

export default function BankingPage() {
  const tenantId = useAuthStore((s) => s.user?.tenant_id);
  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([]);
  const [cashAccounts, setCashAccounts] = useState<CashAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [formMode, setFormMode] = useState<'none' | 'bank' | 'cash'>('none');

  const [bankName, setBankName] = useState('');
  const [accountNumber, setAccountNumber] = useState('');
  const [ifscCode, setIfscCode] = useState('');

  const [cashName, setCashName] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([apiClient.get(BANK_ACCOUNTS_BASE), apiClient.get(CASH_ACCOUNTS_BASE)])
      .then(([bankRes, cashRes]) => {
        setBankAccounts(bankRes.data.items || []);
        setCashAccounts(cashRes.data || []);
      })
      .catch(() => setError('Failed to load banking data'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const resetForm = () => {
    setFormMode('none');
    setBankName('');
    setAccountNumber('');
    setIfscCode('');
    setCashName('');
  };

  const handleCreateBank = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      await apiClient.post(BANK_ACCOUNTS_BASE, { bank_name: bankName, account_number: accountNumber, ifsc_code: ifscCode });
      resetForm();
      load();
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to add bank account');
    } finally {
      setSaving(false);
    }
  };

  const handleCreateCash = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tenantId) return;
    setSaving(true);
    setError('');
    try {
      await apiClient.post(CASH_ACCOUNTS_BASE, { tenant_id: tenantId, name: cashName, is_petty_cash: true });
      resetForm();
      load();
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to add cash account');
    } finally {
      setSaving(false);
    }
  };

  const totalCash = bankAccounts.reduce((sum, b) => sum + Number(b.current_balance), 0) + cashAccounts.reduce((sum, c) => sum + Number(c.balance), 0);

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Banking & Cash Management</h1>
        <div className="flex space-x-2">
          <button onClick={() => setFormMode(formMode === 'bank' ? 'none' : 'bank')} className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700">
            {formMode === 'bank' ? 'Cancel' : 'Add Bank Account'}
          </button>
          <button onClick={() => setFormMode(formMode === 'cash' ? 'none' : 'cash')} className="bg-green-600 text-white px-4 py-2 rounded shadow hover:bg-green-700">
            {formMode === 'cash' ? 'Cancel' : 'Add Cash Account'}
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div className="bg-white p-4 shadow rounded-lg border-l-4 border-blue-500">
          <p className="text-sm text-gray-500 font-medium">Total Cash & Bank Balance</p>
          <p className="text-2xl font-bold">${totalCash.toFixed(2)}</p>
        </div>
        <div className="bg-white p-4 shadow rounded-lg border-l-4 border-yellow-500">
          <p className="text-sm text-gray-500 font-medium">Accounts Tracked</p>
          <p className="text-2xl font-bold text-yellow-600">{bankAccounts.length + cashAccounts.length}</p>
        </div>
      </div>

      {formMode === 'bank' && (
        <form onSubmit={handleCreateBank} className="bg-white shadow rounded-lg p-6 mb-6 space-y-4">
          <h2 className="text-lg font-semibold">Add Bank Account</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Bank Name</label>
              <input type="text" required value={bankName} onChange={(e) => setBankName(e.target.value)} className="w-full p-2 border rounded" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Account Number</label>
              <input type="text" required value={accountNumber} onChange={(e) => setAccountNumber(e.target.value)} className="w-full p-2 border rounded" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">IFSC/Routing Code</label>
              <input type="text" required value={ifscCode} onChange={(e) => setIfscCode(e.target.value)} className="w-full p-2 border rounded" />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={resetForm} className="px-4 py-2 text-gray-600 hover:text-gray-900">Cancel</button>
            <button type="submit" disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Saving...' : 'Save Bank Account'}
            </button>
          </div>
        </form>
      )}

      {formMode === 'cash' && (
        <form onSubmit={handleCreateCash} className="bg-white shadow rounded-lg p-6 mb-6 space-y-4">
          <h2 className="text-lg font-semibold">Add Petty Cash Account</h2>
          <div>
            <label className="block text-sm font-medium mb-1">Name</label>
            <input type="text" required value={cashName} onChange={(e) => setCashName(e.target.value)} className="w-full p-2 border rounded" />
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={resetForm} className="px-4 py-2 text-gray-600 hover:text-gray-900">Cancel</button>
            <button type="submit" disabled={saving || !tenantId} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Saving...' : 'Save Cash Account'}
            </button>
          </div>
        </form>
      )}

      <div className="bg-white shadow rounded-lg overflow-hidden mb-6">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-medium text-gray-900">Accounts Overview</h2>
        </div>
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Account Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Account Number</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Current Balance</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {loading ? (
              <tr><td colSpan={3} className="px-6 py-4 text-center">Loading...</td></tr>
            ) : bankAccounts.length === 0 && cashAccounts.length === 0 ? (
              <tr><td colSpan={3} className="px-6 py-4 text-center text-gray-500">No accounts found.</td></tr>
            ) : (
              <>
                {bankAccounts.map((b) => (
                  <tr key={b.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{b.bank_name}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">****{b.account_number.slice(-4)}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium">${Number(b.current_balance).toFixed(2)}</td>
                  </tr>
                ))}
                {cashAccounts.map((c) => (
                  <tr key={c.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{c.name}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">N/A</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium">${Number(c.balance).toFixed(2)}</td>
                  </tr>
                ))}
              </>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
