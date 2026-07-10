'use client';

import { useEffect, useState, useCallback } from 'react';
import apiClient, { isApiError } from '@/lib/apiClient';
import { useAuthStore } from '@/store/authStore';

interface Category {
  id: string;
  name: string;
}

interface Claim {
  id: string;
  category_id: string;
  amount: number;
  description: string | null;
  status: string;
  created_at: string;
}

const BASE = '/api/v1/finance-ar-ap';

export default function ExpensesPage() {
  const tenantId = useAuthStore((s) => s.user?.tenant_id);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [formMode, setFormMode] = useState<'none' | 'claim' | 'category'>('none');

  const [categoryId, setCategoryId] = useState('');
  const [amount, setAmount] = useState('');
  const [description, setDescription] = useState('');
  const [newCategoryName, setNewCategoryName] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([apiClient.get(`${BASE}/expenses/claims`), apiClient.get(`${BASE}/expenses/categories`)])
      .then(([claimRes, catRes]) => {
        setClaims(claimRes.data || []);
        setCategories(catRes.data || []);
      })
      .catch(() => setError('Failed to load expenses'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const categoryName = (id: string) => categories.find((c) => c.id === id)?.name || id;

  const resetForm = () => {
    setFormMode('none');
    setCategoryId('');
    setAmount('');
    setDescription('');
    setNewCategoryName('');
  };

  const handleCreateCategory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tenantId) return;
    setSaving(true);
    setError('');
    try {
      await apiClient.post(`${BASE}/expenses/categories`, { tenant_id: tenantId, name: newCategoryName });
      resetForm();
      load();
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to create category');
    } finally {
      setSaving(false);
    }
  };

  const handleSubmitClaim = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tenantId) return;
    setSaving(true);
    setError('');
    try {
      // user_id is force-overwritten server-side from the JWT identity.
      await apiClient.post(`${BASE}/expenses/claims`, {
        tenant_id: tenantId,
        user_id: tenantId,
        category_id: categoryId,
        amount: parseFloat(amount),
        description: description || null,
      });
      resetForm();
      load();
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to submit claim');
    } finally {
      setSaving(false);
    }
  };

  const pending = claims.filter((c) => c.status === 'SUBMITTED').length;
  const approved = claims.filter((c) => c.status === 'APPROVED').length;
  const paidTotal = claims.filter((c) => c.status === 'PAID').reduce((sum, c) => sum + Number(c.amount), 0);

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Expense Management</h1>
        <div className="flex gap-2">
          <button onClick={() => setFormMode(formMode === 'category' ? 'none' : 'category')} className="bg-gray-100 text-gray-700 px-4 py-2 rounded shadow hover:bg-gray-200">
            {formMode === 'category' ? 'Cancel' : 'New Category'}
          </button>
          <button onClick={() => setFormMode(formMode === 'claim' ? 'none' : 'claim')} className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700">
            {formMode === 'claim' ? 'Cancel' : 'Submit Claim'}
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-white p-4 shadow rounded-lg border-l-4 border-yellow-500">
          <p className="text-sm text-gray-500 font-medium">Pending Approval</p>
          <p className="text-2xl font-bold text-yellow-600">{pending}</p>
        </div>
        <div className="bg-white p-4 shadow rounded-lg border-l-4 border-green-500">
          <p className="text-sm text-gray-500 font-medium">Approved (Unpaid)</p>
          <p className="text-2xl font-bold">{approved}</p>
        </div>
        <div className="bg-white p-4 shadow rounded-lg border-l-4 border-blue-500">
          <p className="text-sm text-gray-500 font-medium">Paid Total</p>
          <p className="text-2xl font-bold">${paidTotal.toFixed(2)}</p>
        </div>
      </div>

      {formMode === 'category' && (
        <form onSubmit={handleCreateCategory} className="bg-white shadow rounded-lg p-6 mb-6 space-y-4">
          <h2 className="text-lg font-semibold">New Expense Category</h2>
          <input type="text" required value={newCategoryName} onChange={(e) => setNewCategoryName(e.target.value)} placeholder="e.g. Travel" className="w-full p-2 border rounded" />
          <div className="flex justify-end gap-2">
            <button type="button" onClick={resetForm} className="px-4 py-2 text-gray-600 hover:text-gray-900">Cancel</button>
            <button type="submit" disabled={saving || !tenantId} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Saving...' : 'Save Category'}
            </button>
          </div>
        </form>
      )}

      {formMode === 'claim' && (
        <form onSubmit={handleSubmitClaim} className="bg-white shadow rounded-lg p-6 mb-6 space-y-4">
          <h2 className="text-lg font-semibold">Submit Expense Claim</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Category</label>
              <select required value={categoryId} onChange={(e) => setCategoryId(e.target.value)} className="w-full p-2 border rounded">
                <option value="">- Select -</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Amount</label>
              <input type="number" step="0.01" required value={amount} onChange={(e) => setAmount(e.target.value)} className="w-full p-2 border rounded" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Description</label>
              <input type="text" value={description} onChange={(e) => setDescription(e.target.value)} className="w-full p-2 border rounded" />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={resetForm} className="px-4 py-2 text-gray-600 hover:text-gray-900">Cancel</button>
            <button type="submit" disabled={saving || !tenantId} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Saving...' : 'Submit Claim'}
            </button>
          </div>
        </form>
      )}

      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Category</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Description</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Amount</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {loading ? (
              <tr><td colSpan={5} className="px-6 py-4 text-center">Loading...</td></tr>
            ) : claims.length === 0 ? (
              <tr><td colSpan={5} className="px-6 py-4 text-center text-gray-500">No expense claims found.</td></tr>
            ) : claims.map((item) => (
              <tr key={item.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{new Date(item.created_at).toLocaleDateString()}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{categoryName(item.category_id)}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{item.description || '-'}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium">${Number(item.amount).toFixed(2)}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                    item.status === 'APPROVED' ? 'bg-green-100 text-green-800' :
                    item.status === 'PAID' ? 'bg-blue-100 text-blue-800' :
                    item.status === 'REJECTED' ? 'bg-red-100 text-red-800' :
                    'bg-yellow-100 text-yellow-800'
                  }`}>{item.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
