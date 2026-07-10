'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useCrudResource } from '@/hooks/useCrudResource';

interface Brand {
  id: string;
  name: string;
  description: string | null;
  website: string | null;
  is_active: boolean;
}

const BASE = '/api/v1/universal-inventory/brands';

export default function BrandsPage() {
  const { data: brands, loading, error, saving, create, update, remove } = useCrudResource<Brand>(BASE);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [website, setWebsite] = useState('');

  const resetForm = () => {
    setShowForm(false);
    setEditingId(null);
    setName('');
    setWebsite('');
  };

  const handleEdit = (brand: Brand) => {
    setEditingId(brand.id);
    setName(brand.name);
    setWebsite(brand.website || '');
    setShowForm(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = { name, website: website || null };
    const ok = editingId ? await update(editingId, payload) : await create(payload);
    if (ok) resetForm();
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this brand?')) return;
    await remove(id);
  };

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/universal-inventory" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Dashboard</Link>
          <h1 className="text-2xl font-bold">Brand Management</h1>
        </div>
        <button onClick={() => (showForm ? resetForm() : setShowForm(true))} className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700 transition-colors">
          {showForm ? 'Cancel' : 'Create Brand'}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md mb-8 border border-gray-200 dark:border-gray-700 space-y-4">
          <h2 className="text-lg font-semibold">{editingId ? 'Edit Brand' : 'Create New Brand'}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Name</label>
              <input type="text" required value={name} onChange={(e) => setName(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Website</label>
              <input type="text" value={website} onChange={(e) => setWebsite(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={resetForm} className="px-4 py-2 text-gray-600 hover:text-gray-900">Cancel</button>
            <button type="submit" disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Saving...' : editingId ? 'Update Brand' : 'Save Brand'}
            </button>
          </div>
        </form>
      )}

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden border border-gray-200 dark:border-gray-700">
        <table className="min-w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
            <tr>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Brand Name</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Website</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Status</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {loading ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={4}>Loading brands...</td></tr>
            ) : brands.length === 0 ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={4}>No brands found. Create one to begin.</td></tr>
            ) : brands.map((brand) => (
              <tr key={brand.id}>
                <td className="px-6 py-4 font-medium">{brand.name}</td>
                <td className="px-6 py-4 text-gray-500">{brand.website || '-'}</td>
                <td className="px-6 py-4">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${brand.is_active ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-gray-100 text-gray-600 border border-gray-200'}`}>
                    {brand.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td className="px-6 py-4 space-x-3">
                  <button onClick={() => handleEdit(brand)} className="text-blue-600 hover:underline">Edit</button>
                  <button onClick={() => handleDelete(brand.id)} className="text-red-600 hover:underline">Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
