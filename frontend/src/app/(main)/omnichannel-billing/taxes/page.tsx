'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useCrudResource } from '@/hooks/useCrudResource';

interface TaxConfig {
  id: string;
  name: string;
  cgst_rate: number;
  sgst_rate: number;
  igst_rate: number;
  is_active: boolean;
}

const BASE = '/api/v1/omnichannel-billing/taxes/configurations';

export default function TaxesPage() {
  const { data: configs, loading, error, saving, create } = useCrudResource<TaxConfig>(BASE);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState('');
  const [cgst, setCgst] = useState('0');
  const [sgst, setSgst] = useState('0');
  const [igst, setIgst] = useState('0');

  const resetForm = () => {
    setShowForm(false);
    setName('');
    setCgst('0');
    setSgst('0');
    setIgst('0');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const ok = await create({
      name,
      cgst_rate: parseFloat(cgst) || 0,
      sgst_rate: parseFloat(sgst) || 0,
      igst_rate: parseFloat(igst) || 0,
    });
    if (ok) resetForm();
  };

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/omnichannel-billing/analytics/dashboard" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Billing Dashboard</Link>
          <h1 className="text-2xl font-bold">Tax & GST Engine</h1>
          <p className="text-gray-600 dark:text-gray-400">Configure Tax Rates.</p>
        </div>
        <button onClick={() => (showForm ? resetForm() : setShowForm(true))} className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700 transition-colors">
          {showForm ? 'Cancel' : 'Add Configuration'}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md mb-8 border border-gray-200 dark:border-gray-700 space-y-4">
          <h2 className="text-lg font-semibold">New Tax Configuration</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Name</label>
              <input type="text" required value={name} onChange={(e) => setName(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">CGST %</label>
              <input type="number" step="0.01" value={cgst} onChange={(e) => setCgst(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">SGST %</label>
              <input type="number" step="0.01" value={sgst} onChange={(e) => setSgst(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">IGST %</label>
              <input type="number" step="0.01" value={igst} onChange={(e) => setIgst(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={resetForm} className="px-4 py-2 text-gray-600 hover:text-gray-900">Cancel</button>
            <button type="submit" disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Saving...' : 'Save Configuration'}
            </button>
          </div>
        </form>
      )}

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden border border-gray-200 dark:border-gray-700">
        <table className="min-w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
            <tr>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Configuration Name</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">CGST %</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">SGST %</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">IGST %</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {loading ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={5}>Loading configurations...</td></tr>
            ) : configs.length === 0 ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={5}>No tax configurations found.</td></tr>
            ) : configs.map((c) => (
              <tr key={c.id}>
                <td className="px-6 py-4 font-medium">{c.name}</td>
                <td className="px-6 py-4">{c.cgst_rate}%</td>
                <td className="px-6 py-4">{c.sgst_rate}%</td>
                <td className="px-6 py-4">{c.igst_rate}%</td>
                <td className="px-6 py-4">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${c.is_active ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-gray-100 text-gray-600 border border-gray-200'}`}>
                    {c.is_active ? 'Active' : 'Inactive'}
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
