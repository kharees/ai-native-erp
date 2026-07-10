'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import apiClient, { isApiError } from '@/lib/apiClient';

interface Warehouse {
  id: string;
  name: string;
}

interface Bin {
  id: string;
  warehouse_id: string;
  code: string;
  name: string;
  aisle: string | null;
  rack: string | null;
  shelf: string | null;
  max_weight: number;
  max_volume: number;
}

const BINS_BASE = '/api/v1/universal-warehousing/bins';
const WAREHOUSES_BASE = '/api/v1/universal-warehousing/warehouses';

export default function BinsPage() {
  const [bins, setBins] = useState<Bin[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const [warehouseId, setWarehouseId] = useState('');
  const [code, setCode] = useState('');
  const [name, setName] = useState('');
  const [aisle, setAisle] = useState('');
  const [rack, setRack] = useState('');
  const [shelf, setShelf] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([apiClient.get(BINS_BASE), apiClient.get(WAREHOUSES_BASE)])
      .then(([binsRes, whRes]) => {
        setBins(binsRes.data.items || []);
        setWarehouses(whRes.data.items || []);
      })
      .catch(() => setError('Failed to load bins'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const warehouseName = (id: string) => warehouses.find((w) => w.id === id)?.name || '-';

  const resetForm = () => {
    setShowForm(false);
    setWarehouseId('');
    setCode('');
    setName('');
    setAisle('');
    setRack('');
    setShelf('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      await apiClient.post(BINS_BASE, {
        warehouse_id: warehouseId,
        code,
        name,
        aisle: aisle || null,
        rack: rack || null,
        shelf: shelf || null,
      });
      resetForm();
      load();
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to create bin');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/universal-inventory/warehouses" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Warehouses</Link>
          <h1 className="text-2xl font-bold">Bin Management</h1>
          <p className="text-gray-500 text-sm mt-1">Configure micro-locations using flat dimensional attributes.</p>
        </div>
        <button onClick={() => (showForm ? resetForm() : setShowForm(true))} className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700 transition-colors">
          {showForm ? 'Cancel' : 'Create Bin'}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md mb-8 border border-gray-200 dark:border-gray-700 space-y-4">
          <h2 className="text-lg font-semibold">Create New Bin</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Warehouse</label>
              <select required value={warehouseId} onChange={(e) => setWarehouseId(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600">
                <option value="">- Select -</option>
                {warehouses.map((w) => (
                  <option key={w.id} value={w.id}>{w.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Bin Code</label>
              <input type="text" required value={code} onChange={(e) => setCode(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Name</label>
              <input type="text" required value={name} onChange={(e) => setName(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Aisle</label>
              <input type="text" value={aisle} onChange={(e) => setAisle(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Rack</label>
              <input type="text" value={rack} onChange={(e) => setRack(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Shelf</label>
              <input type="text" value={shelf} onChange={(e) => setShelf(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={resetForm} className="px-4 py-2 text-gray-600 hover:text-gray-900">Cancel</button>
            <button type="submit" disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Saving...' : 'Save Bin'}
            </button>
          </div>
        </form>
      )}

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden border border-gray-200 dark:border-gray-700">
        <table className="min-w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
            <tr>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Bin Code</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Warehouse</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Aisle/Rack/Shelf</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Capacity Metrics</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {loading ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={4}>Loading bins...</td></tr>
            ) : bins.length === 0 ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={4}>No bins found.</td></tr>
            ) : bins.map((bin) => (
              <tr key={bin.id}>
                <td className="px-6 py-4 font-mono">{bin.code}</td>
                <td className="px-6 py-4">{warehouseName(bin.warehouse_id)}</td>
                <td className="px-6 py-4 text-gray-500">{[bin.aisle, bin.rack, bin.shelf].filter(Boolean).join(' / ') || '-'}</td>
                <td className="px-6 py-4 text-gray-500">{bin.max_weight}kg / {bin.max_volume}m3</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
