'use client';

import { useEffect, useState, useCallback } from 'react';
import apiClient, { isApiError } from '@/lib/apiClient';
import { useAuthStore } from '@/store/authStore';

interface Account {
  id: string;
  account_code: string;
  name: string;
}

interface Budget {
  id: string;
  name: string;
  fiscal_year: string;
  period_type: string;
  status: string;
}

const BASE = '/api/v1/finance-assets';

export default function BudgetingPage() {
  const tenantId = useAuthStore((s) => s.user?.tenant_id);
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const [name, setName] = useState('');
  const [fiscalYear, setFiscalYear] = useState(String(new Date().getFullYear()));
  const [periodType, setPeriodType] = useState('ANNUAL');
  const [lineAccountId, setLineAccountId] = useState('');
  const [lineAmount, setLineAmount] = useState('');
  const [lines, setLines] = useState<{ account_id: string; allocated_amount: number }[]>([]);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([apiClient.get(`${BASE}/budgets`), apiClient.get('/api/v1/finance-core/accounts')])
      .then(([budgetRes, accountRes]) => {
        setBudgets(budgetRes.data || []);
        setAccounts(accountRes.data || []);
      })
      .catch(() => setError('Failed to load budgets'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const accountLabel = (id: string) => {
    const a = accounts.find((acc) => acc.id === id);
    return a ? `${a.name} (${a.account_code})` : id;
  };

  const resetForm = () => {
    setShowForm(false);
    setName('');
    setFiscalYear(String(new Date().getFullYear()));
    setPeriodType('ANNUAL');
    setLines([]);
    setLineAccountId('');
    setLineAmount('');
  };

  const addLine = () => {
    if (!lineAccountId || !lineAmount) return;
    setLines((prev) => [...prev, { account_id: lineAccountId, allocated_amount: parseFloat(lineAmount) }]);
    setLineAccountId('');
    setLineAmount('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tenantId) return;
    setSaving(true);
    setError('');
    try {
      await apiClient.post(`${BASE}/budgets`, {
        tenant_id: tenantId,
        name,
        fiscal_year: fiscalYear,
        period_type: periodType,
        lines,
      });
      resetForm();
      load();
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to create budget');
    } finally {
      setSaving(false);
    }
  };

  const totalAllocated = lines.reduce((sum, l) => sum + l.allocated_amount, 0);

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold">Budget Management</h1>
          <p className="text-gray-500 text-sm">Planning and allocation by account.</p>
        </div>
        <button onClick={() => (showForm ? resetForm() : setShowForm(true))} className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700">
          {showForm ? 'Cancel' : '+ Create Budget'}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white shadow rounded-lg p-6 mb-6 space-y-4">
          <h2 className="text-lg font-semibold">New Budget</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Name</label>
              <input type="text" required value={name} onChange={(e) => setName(e.target.value)} className="w-full p-2 border rounded" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Fiscal Year</label>
              <input type="text" required value={fiscalYear} onChange={(e) => setFiscalYear(e.target.value)} className="w-full p-2 border rounded" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Period</label>
              <select value={periodType} onChange={(e) => setPeriodType(e.target.value)} className="w-full p-2 border rounded">
                <option value="ANNUAL">Annual</option>
                <option value="QUARTERLY">Quarterly</option>
                <option value="MONTHLY">Monthly</option>
              </select>
            </div>
          </div>

          <div className="border-t pt-4">
            <h3 className="text-sm font-semibold mb-2">Budget Lines</h3>
            {lines.length > 0 && (
              <ul className="mb-3 space-y-1">
                {lines.map((l, i) => (
                  <li key={i} className="text-sm p-2 bg-gray-50 rounded border flex justify-between">
                    <span>{accountLabel(l.account_id)}</span>
                    <span className="font-medium">${l.allocated_amount.toFixed(2)}</span>
                  </li>
                ))}
                <li className="text-sm font-semibold flex justify-between pt-1">
                  <span>Total Allocated</span>
                  <span>${totalAllocated.toFixed(2)}</span>
                </li>
              </ul>
            )}
            <div className="flex gap-2">
              <select value={lineAccountId} onChange={(e) => setLineAccountId(e.target.value)} className="flex-1 p-2 border rounded">
                <option value="">- Select account -</option>
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>{a.name} ({a.account_code})</option>
                ))}
              </select>
              <input type="number" step="0.01" placeholder="Amount" value={lineAmount} onChange={(e) => setLineAmount(e.target.value)} className="w-40 p-2 border rounded" />
              <button type="button" onClick={addLine} className="bg-gray-200 px-4 py-2 rounded text-sm hover:bg-gray-300">Add Line</button>
            </div>
          </div>

          <div className="flex justify-end gap-2">
            <button type="button" onClick={resetForm} className="px-4 py-2 text-gray-600 hover:text-gray-900">Cancel</button>
            <button type="submit" disabled={saving || !tenantId} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Saving...' : 'Save Budget'}
            </button>
          </div>
        </form>
      )}

      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-bold mb-4 border-b pb-2">Budgets</h2>
        {loading ? (
          <p className="text-sm text-gray-500">Loading budgets...</p>
        ) : budgets.length === 0 ? (
          <p className="text-sm text-gray-500">No budgets created yet.</p>
        ) : (
          <div className="space-y-4">
            {budgets.map((budget) => (
              <div key={budget.id} className="border p-4 rounded-lg hover:shadow-md transition">
                <div className="flex justify-between items-center mb-2">
                  <h3 className="font-bold text-gray-800">{budget.name}</h3>
                  <span className={`px-2 py-1 text-xs font-semibold rounded-full ${budget.status === 'ACTIVE' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                    {budget.status}
                  </span>
                </div>
                <div className="flex justify-between text-sm text-gray-600">
                  <span>Period: {budget.period_type}</span>
                  <span>Fiscal Year: {budget.fiscal_year}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
