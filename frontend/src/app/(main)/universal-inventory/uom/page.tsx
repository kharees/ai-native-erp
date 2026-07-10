'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useCrudResource } from '@/hooks/useCrudResource';

interface UOM {
  id: string;
  name: string;
  abbreviation: string;
  conversion_factor: number;
  is_active: boolean;
}

const BASE = '/api/v1/universal-inventory/uoms';

export default function UOMPage() {
  const { data: uoms, loading, error, saving, create, update, remove } = useCrudResource<UOM>(BASE);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [abbreviation, setAbbreviation] = useState('');
  const [conversionFactor, setConversionFactor] = useState('1');

  const resetForm = () => {
    setShowForm(false);
    setEditingId(null);
    setName('');
    setAbbreviation('');
    setConversionFactor('1');
  };

  const handleEdit = (uom: UOM) => {
    setEditingId(uom.id);
    setName(uom.name);
    setAbbreviation(uom.abbreviation);
    setConversionFactor(String(uom.conversion_factor));
    setShowForm(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = { name, abbreviation, conversion_factor: parseFloat(conversionFactor) || 1 };
    const ok = editingId ? await update(editingId, payload) : await create(payload);
    if (ok) resetForm();
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this UOM?')) return;
    await remove(id);
  };

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/universal-inventory" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Dashboard</Link>
          <h1 className="text-2xl font-bold">Unit of Measure (UOM) Engine</h1>
        </div>
        <button onClick={() => (showForm ? resetForm() : setShowForm(true))} className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700 transition-colors">
          {showForm ? 'Cancel' : 'Create UOM'}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md mb-8 border border-gray-200 dark:border-gray-700 space-y-4">
          <h2 className="text-lg font-semibold">{editingId ? 'Edit UOM' : 'Create New UOM'}</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Name</label>
              <input type="text" required value={name} onChange={(e) => setName(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Abbreviation</label>
              <input type="text" required value={abbreviation} onChange={(e) => setAbbreviation(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Conversion Factor</label>
              <input type="number" step="0.0001" value={conversionFactor} onChange={(e) => setConversionFactor(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={resetForm} className="px-4 py-2 text-gray-600 hover:text-gray-900">Cancel</button>
            <button type="submit" disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Saving...' : editingId ? 'Update UOM' : 'Save UOM'}
            </button>
          </div>
        </form>
      )}

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden border border-gray-200 dark:border-gray-700">
        <table className="min-w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
            <tr>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">UOM Name</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Abbreviation</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Conversion Factor</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Status</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {loading ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={5}>Loading UOMs...</td></tr>
            ) : uoms.length === 0 ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={5}>No UOMs found. Create one to begin establishing conversion logic.</td></tr>
            ) : uoms.map((uom) => (
              <tr key={uom.id}>
                <td className="px-6 py-4 font-medium">{uom.name}</td>
                <td className="px-6 py-4 text-gray-500">{uom.abbreviation}</td>
                <td className="px-6 py-4 text-gray-500">{uom.conversion_factor}</td>
                <td className="px-6 py-4">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${uom.is_active ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-gray-100 text-gray-600 border border-gray-200'}`}>
                    {uom.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td className="px-6 py-4 space-x-3">
                  <button onClick={() => handleEdit(uom)} className="text-blue-600 hover:underline">Edit</button>
                  <button onClick={() => handleDelete(uom.id)} className="text-red-600 hover:underline">Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
