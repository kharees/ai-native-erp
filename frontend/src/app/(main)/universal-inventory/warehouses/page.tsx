'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useCrudResource } from '@/hooks/useCrudResource';

interface Warehouse {
  id: string;
  code: string;
  name: string;
  type: string | null;
  status: string;
  capacity_sqft: number;
  is_active: boolean;
}

const BASE = '/api/v1/universal-warehousing/warehouses';

export default function WarehousesDashboard() {
  // Backend only exposes Create + Read for warehouses (no PATCH/DELETE route) -
  // matches the finance account-groups precedent of intentionally limited CRUD.
  const { data: warehouses, loading, error, saving, create } = useCrudResource<Warehouse>(BASE);
  const [showForm, setShowForm] = useState(false);
  const [code, setCode] = useState('');
  const [name, setName] = useState('');
  const [type, setType] = useState('main');
  const [capacitySqft, setCapacitySqft] = useState('0');

  const resetForm = () => {
    setShowForm(false);
    setCode('');
    setName('');
    setType('main');
    setCapacitySqft('0');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const ok = await create({ code, name, type, capacity_sqft: parseFloat(capacitySqft) || 0 });
    if (ok) resetForm();
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/universal-inventory" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Inventory Dashboard</Link>
          <h1 className="text-3xl font-bold">Universal Warehousing</h1>
        </div>
        <div className="space-x-2">
          <Link href="/universal-inventory/warehouses/bins">
            <button className="bg-gray-200 text-gray-800 px-4 py-2 rounded shadow hover:bg-gray-300 transition-colors">Manage Bins</button>
          </Link>
          <button onClick={() => (showForm ? resetForm() : setShowForm(true))} className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700 transition-colors">
            {showForm ? 'Cancel' : 'Create Warehouse'}
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md border border-gray-200 dark:border-gray-700 space-y-4">
          <h2 className="text-lg font-semibold">Create New Warehouse</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Code</label>
              <input type="text" required value={code} onChange={(e) => setCode(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Name</label>
              <input type="text" required value={name} onChange={(e) => setName(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Type</label>
              <select value={type} onChange={(e) => setType(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600">
                <option value="main">main</option>
                <option value="transit">transit</option>
                <option value="virtual">virtual</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Capacity (sqft)</label>
              <input type="number" step="0.01" value={capacitySqft} onChange={(e) => setCapacitySqft(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={resetForm} className="px-4 py-2 text-gray-600 hover:text-gray-900">Cancel</button>
            <button type="submit" disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Saving...' : 'Save Warehouse'}
            </button>
          </div>
        </form>
      )}

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden border border-gray-200 dark:border-gray-700">
        <table className="min-w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
            <tr>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Warehouse Code</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Name</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Type</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Capacity</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {loading ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={5}>Loading warehouses...</td></tr>
            ) : warehouses.length === 0 ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={5}>No warehouses found. Configure your first location.</td></tr>
            ) : warehouses.map((wh) => (
              <tr key={wh.id}>
                <td className="px-6 py-4 font-mono">{wh.code}</td>
                <td className="px-6 py-4 font-medium">{wh.name}</td>
                <td className="px-6 py-4 text-gray-500">{wh.type || '-'}</td>
                <td className="px-6 py-4 text-gray-500">{wh.capacity_sqft} sqft</td>
                <td className="px-6 py-4">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                    {wh.status}
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
