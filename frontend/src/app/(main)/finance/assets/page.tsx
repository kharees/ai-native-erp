'use client';

import { useEffect, useState, useCallback } from 'react';
import apiClient, { isApiError } from '@/lib/apiClient';
import { useAuthStore } from '@/store/authStore';

interface AssetCategory {
  id: string;
  name: string;
  depreciation_method: string;
  default_depreciation_rate: number;
}

interface Asset {
  id: string;
  category_id: string;
  asset_code: string;
  name: string;
  acquisition_cost: number;
  current_value: number;
  depreciation_method: string;
  status: string;
}

const BASE = '/api/v1/finance-assets';

export default function AssetsPage() {
  const tenantId = useAuthStore((s) => s.user?.tenant_id);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [categories, setCategories] = useState<AssetCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [formMode, setFormMode] = useState<'none' | 'asset' | 'category'>('none');
  const [runningDepreciation, setRunningDepreciation] = useState(false);

  const [categoryId, setCategoryId] = useState('');
  const [assetCode, setAssetCode] = useState('');
  const [assetName, setAssetName] = useState('');
  const [acquisitionCost, setAcquisitionCost] = useState('');

  const [newCategoryName, setNewCategoryName] = useState('');
  const [depreciationMethod, setDepreciationMethod] = useState('SLM');
  const [depreciationRate, setDepreciationRate] = useState('10');

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([apiClient.get(`${BASE}/assets`), apiClient.get(`${BASE}/assets/categories`)])
      .then(([assetRes, catRes]) => {
        setAssets(assetRes.data || []);
        setCategories(catRes.data || []);
      })
      .catch(() => setError('Failed to load fixed assets'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const categoryName = (id: string) => categories.find((c) => c.id === id)?.name || id;

  const resetForm = () => {
    setFormMode('none');
    setCategoryId('');
    setAssetCode('');
    setAssetName('');
    setAcquisitionCost('');
    setNewCategoryName('');
    setDepreciationMethod('SLM');
    setDepreciationRate('10');
  };

  const handleCreateCategory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tenantId) return;
    setSaving(true);
    setError('');
    try {
      await apiClient.post(`${BASE}/assets/categories`, {
        tenant_id: tenantId,
        name: newCategoryName,
        depreciation_method: depreciationMethod,
        default_depreciation_rate: parseFloat(depreciationRate),
      });
      resetForm();
      load();
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to create category');
    } finally {
      setSaving(false);
    }
  };

  const handleCreateAsset = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tenantId) return;
    const category = categories.find((c) => c.id === categoryId);
    if (!category) return;
    setSaving(true);
    setError('');
    try {
      const cost = parseFloat(acquisitionCost);
      await apiClient.post(`${BASE}/assets`, {
        tenant_id: tenantId,
        category_id: categoryId,
        asset_code: assetCode,
        name: assetName,
        acquisition_date: new Date().toISOString(),
        acquisition_cost: cost,
        current_value: cost,
        depreciation_method: category.depreciation_method,
        depreciation_rate: category.default_depreciation_rate,
      });
      resetForm();
      load();
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to create asset');
    } finally {
      setSaving(false);
    }
  };

  const handleRunDepreciation = async () => {
    setRunningDepreciation(true);
    setError('');
    try {
      await apiClient.post(`${BASE}/assets/run-depreciation`);
      load();
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to run depreciation');
    } finally {
      setRunningDepreciation(false);
    }
  };

  const totalCost = assets.reduce((sum, a) => sum + Number(a.acquisition_cost), 0);
  const totalBookValue = assets.reduce((sum, a) => sum + Number(a.current_value), 0);
  const totalDepreciation = totalCost - totalBookValue;

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold">Fixed Asset Management</h1>
          <p className="text-gray-500 text-sm">Asset Register & Depreciation</p>
        </div>
        <div className="space-x-2">
          <button onClick={handleRunDepreciation} disabled={runningDepreciation} className="bg-white border text-gray-700 px-4 py-2 rounded shadow hover:bg-gray-50 disabled:opacity-50">
            {runningDepreciation ? 'Running...' : 'Run Depreciation'}
          </button>
          <button onClick={() => setFormMode(formMode === 'category' ? 'none' : 'category')} className="bg-gray-100 text-gray-700 px-4 py-2 rounded shadow hover:bg-gray-200">
            {formMode === 'category' ? 'Cancel' : 'New Category'}
          </button>
          <button onClick={() => setFormMode(formMode === 'asset' ? 'none' : 'asset')} className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700">
            {formMode === 'asset' ? 'Cancel' : '+ Add Asset'}
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white p-4 shadow rounded-lg border-t-4 border-gray-800">
          <p className="text-sm text-gray-500 font-medium">Total Assets</p>
          <p className="text-3xl font-bold">{assets.length}</p>
        </div>
        <div className="bg-white p-4 shadow rounded-lg border-t-4 border-blue-500">
          <p className="text-sm text-gray-500 font-medium">Acquisition Cost</p>
          <p className="text-3xl font-bold">${totalCost.toLocaleString()}</p>
        </div>
        <div className="bg-white p-4 shadow rounded-lg border-t-4 border-green-500">
          <p className="text-sm text-gray-500 font-medium">Current Book Value</p>
          <p className="text-3xl font-bold text-green-600">${totalBookValue.toLocaleString()}</p>
        </div>
        <div className="bg-white p-4 shadow rounded-lg border-t-4 border-red-500">
          <p className="text-sm text-gray-500 font-medium">Accum. Depreciation</p>
          <p className="text-3xl font-bold text-red-600">${totalDepreciation.toLocaleString()}</p>
        </div>
      </div>

      {formMode === 'category' && (
        <form onSubmit={handleCreateCategory} className="bg-white shadow rounded-lg p-6 mb-6 space-y-4">
          <h2 className="text-lg font-semibold">New Asset Category</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Name</label>
              <input type="text" required value={newCategoryName} onChange={(e) => setNewCategoryName(e.target.value)} className="w-full p-2 border rounded" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Depreciation Method</label>
              <select value={depreciationMethod} onChange={(e) => setDepreciationMethod(e.target.value)} className="w-full p-2 border rounded">
                <option value="SLM">Straight Line (SLM)</option>
                <option value="WDV">Written Down Value (WDV)</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Default Rate (%)</label>
              <input type="number" step="0.01" value={depreciationRate} onChange={(e) => setDepreciationRate(e.target.value)} className="w-full p-2 border rounded" />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={resetForm} className="px-4 py-2 text-gray-600 hover:text-gray-900">Cancel</button>
            <button type="submit" disabled={saving || !tenantId} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Saving...' : 'Save Category'}
            </button>
          </div>
        </form>
      )}

      {formMode === 'asset' && (
        <form onSubmit={handleCreateAsset} className="bg-white shadow rounded-lg p-6 mb-6 space-y-4">
          <h2 className="text-lg font-semibold">Add New Asset</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
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
              <label className="block text-sm font-medium mb-1">Asset Code</label>
              <input type="text" required value={assetCode} onChange={(e) => setAssetCode(e.target.value)} className="w-full p-2 border rounded" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Name</label>
              <input type="text" required value={assetName} onChange={(e) => setAssetName(e.target.value)} className="w-full p-2 border rounded" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Acquisition Cost</label>
              <input type="number" step="0.01" required value={acquisitionCost} onChange={(e) => setAcquisitionCost(e.target.value)} className="w-full p-2 border rounded" />
            </div>
          </div>
          {categories.length === 0 && (
            <p className="text-sm text-yellow-600">Create an asset category first.</p>
          )}
          <div className="flex justify-end gap-2">
            <button type="button" onClick={resetForm} className="px-4 py-2 text-gray-600 hover:text-gray-900">Cancel</button>
            <button type="submit" disabled={saving || !tenantId || categories.length === 0} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Saving...' : 'Save Asset'}
            </button>
          </div>
        </form>
      )}

      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Asset Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Cost</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Book Value</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Method</th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Status</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {loading ? (
              <tr><td colSpan={7} className="px-6 py-4 text-center">Loading asset register...</td></tr>
            ) : assets.length === 0 ? (
              <tr><td colSpan={7} className="px-6 py-4 text-center text-gray-500">No assets registered.</td></tr>
            ) : assets.map((item) => (
              <tr key={item.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{item.asset_code}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{item.name}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{categoryName(item.category_id)}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium">${Number(item.acquisition_cost).toLocaleString()}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium text-green-600">${Number(item.current_value).toLocaleString()}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{item.depreciation_method}</td>
                <td className="px-6 py-4 whitespace-nowrap text-center">
                  <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                    {item.status}
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
