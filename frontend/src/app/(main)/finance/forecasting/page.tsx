'use client';

import { useEffect, useState, useCallback } from 'react';
import apiClient, { isApiError } from '@/lib/apiClient';
import { useAuthStore } from '@/store/authStore';

interface Forecast {
  id: string;
  name: string;
  target_period: string;
  forecast_type: string;
  predicted_amount: number;
}

const BASE = '/api/v1/finance-assets';

export default function ForecastingPage() {
  const tenantId = useAuthStore((s) => s.user?.tenant_id);
  const [forecasts, setForecasts] = useState<Forecast[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const [name, setName] = useState('');
  const [targetPeriod, setTargetPeriod] = useState('');
  const [forecastType, setForecastType] = useState('REVENUE');
  const [predictedAmount, setPredictedAmount] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    apiClient
      .get(`${BASE}/forecasts`)
      .then((res) => setForecasts(res.data || []))
      .catch(() => setError('Failed to load forecasts'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const resetForm = () => {
    setShowForm(false);
    setName('');
    setTargetPeriod('');
    setForecastType('REVENUE');
    setPredictedAmount('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tenantId) return;
    setSaving(true);
    setError('');
    try {
      await apiClient.post(`${BASE}/forecasts`, {
        tenant_id: tenantId,
        name,
        target_period: targetPeriod,
        forecast_type: forecastType,
        predicted_amount: parseFloat(predictedAmount),
      });
      resetForm();
      load();
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to create forecast');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold">Financial Forecasting</h1>
          <p className="text-gray-500 text-sm">Revenue, expense, and cash flow targets.</p>
        </div>
        <button onClick={() => (showForm ? resetForm() : setShowForm(true))} className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700">
          {showForm ? 'Cancel' : 'Create Forecast'}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white shadow rounded-lg p-6 mb-6 space-y-4">
          <h2 className="text-lg font-semibold">New Forecast</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Name</label>
              <input type="text" required value={name} onChange={(e) => setName(e.target.value)} className="w-full p-2 border rounded" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Target Period</label>
              <input type="text" required placeholder="e.g. Q3-2026" value={targetPeriod} onChange={(e) => setTargetPeriod(e.target.value)} className="w-full p-2 border rounded" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Type</label>
              <select value={forecastType} onChange={(e) => setForecastType(e.target.value)} className="w-full p-2 border rounded">
                <option value="REVENUE">Revenue</option>
                <option value="EXPENSE">Expense</option>
                <option value="CASH_FLOW">Cash Flow</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Predicted Amount</label>
              <input type="number" step="0.01" required value={predictedAmount} onChange={(e) => setPredictedAmount(e.target.value)} className="w-full p-2 border rounded" />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={resetForm} className="px-4 py-2 text-gray-600 hover:text-gray-900">Cancel</button>
            <button type="submit" disabled={saving || !tenantId} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Saving...' : 'Save Forecast'}
            </button>
          </div>
        </form>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {loading ? (
          <p className="text-sm text-gray-500 col-span-3">Loading forecasts...</p>
        ) : forecasts.length === 0 ? (
          <p className="text-sm text-gray-500 col-span-3">No forecasts created yet.</p>
        ) : forecasts.map((forecast) => (
          <div key={forecast.id} className="bg-white shadow rounded-lg p-6 flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-center mb-4 border-b pb-2">
                <h3 className="font-bold text-gray-800 capitalize">{forecast.forecast_type.replace('_', ' ').toLowerCase()} Forecast</h3>
                <span className="text-xs text-gray-500 font-mono bg-gray-100 px-2 py-1 rounded">{forecast.target_period}</span>
              </div>
              <p className="text-sm text-gray-500">{forecast.name}</p>
              <p className="text-3xl font-bold text-indigo-700 mt-2">${Number(forecast.predicted_amount).toLocaleString()}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
