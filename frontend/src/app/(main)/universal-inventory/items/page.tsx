'use client';

import { useEffect, useState, useCallback } from 'react';
import apiClient, { isApiError } from '@/lib/apiClient';

interface Category {
  id: string;
  name: string;
}

interface Item {
  id: string;
  item_code: string;
  sku: string;
  name: string;
  status: string;
  category_id: string | null;
  attributes: Record<string, string>;
}

const ITEMS_BASE = '/api/v1/universal-inventory/items';
const CATEGORIES_BASE = '/api/v1/universal-inventory/categories';

export default function ItemMasterPage() {
  const [items, setItems] = useState<Item[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [itemCode, setItemCode] = useState('');
  const [sku, setSku] = useState('');
  const [name, setName] = useState('');
  const [status, setStatus] = useState('draft');
  const [categoryId, setCategoryId] = useState('');
  const [attrs, setAttrs] = useState<{ key: string; value: string }[]>([]);
  const [attrKey, setAttrKey] = useState('');
  const [attrValue, setAttrValue] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([
      apiClient.get(ITEMS_BASE),
      apiClient.get(CATEGORIES_BASE),
    ])
      .then(([itemsRes, catsRes]) => {
        setItems(itemsRes.data.items || []);
        setCategories(catsRes.data.items || []);
      })
      .catch(() => setError('Failed to load items'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const resetForm = () => {
    setShowForm(false);
    setEditingId(null);
    setItemCode('');
    setSku('');
    setName('');
    setStatus('draft');
    setCategoryId('');
    setAttrs([]);
    setAttrKey('');
    setAttrValue('');
  };

  const handleEdit = (item: Item) => {
    setEditingId(item.id);
    setItemCode(item.item_code);
    setSku(item.sku);
    setName(item.name);
    setStatus(item.status);
    setCategoryId(item.category_id || '');
    setAttrs(Object.entries(item.attributes || {}).map(([key, value]) => ({ key, value: String(value) })));
    setShowForm(true);
  };

  const addAttribute = () => {
    if (!attrKey.trim()) return;
    setAttrs((prev) => [...prev, { key: attrKey.trim(), value: attrValue.trim() }]);
    setAttrKey('');
    setAttrValue('');
  };

  const removeAttribute = (key: string) => {
    setAttrs((prev) => prev.filter((a) => a.key !== key));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    const attributes = Object.fromEntries(attrs.map((a) => [a.key, a.value]));
    const payload = {
      item_code: itemCode,
      sku,
      name,
      status,
      category_id: categoryId || null,
      attributes,
    };
    try {
      if (editingId) {
        await apiClient.patch(`${ITEMS_BASE}/${editingId}`, payload);
      } else {
        await apiClient.post(ITEMS_BASE, payload);
      }
      resetForm();
      load();
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to save item');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this item?')) return;
    try {
      await apiClient.delete(`${ITEMS_BASE}/${id}`);
      load();
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to delete item');
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Universal Item Master</h1>
        <button onClick={() => (showForm ? resetForm() : setShowForm(true))} className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700 transition-colors">
          {showForm ? 'Cancel' : 'Create Item'}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      {showForm && (
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md mb-8 border border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold mb-4">{editingId ? 'Edit Item' : 'Create New Universal Item'}</h2>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Item Code</label>
                <input type="text" required value={itemCode} onChange={(e) => setItemCode(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">SKU</label>
                <input type="text" required value={sku} onChange={(e) => setSku(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Item Name</label>
                <input type="text" required value={name} onChange={(e) => setName(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Category</label>
                <select value={categoryId} onChange={(e) => setCategoryId(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600">
                  <option value="">- None -</option>
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Status</label>
                <select value={status} onChange={(e) => setStatus(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600">
                  <option value="draft">draft</option>
                  <option value="active">active</option>
                  <option value="inactive">inactive</option>
                </select>
              </div>
            </div>

            <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
              <h3 className="text-md font-medium mb-2">Dynamic JSONB Attributes</h3>
              <p className="text-xs text-gray-500 mb-4">Add custom metadata fields without schema changes.</p>

              {attrs.length > 0 && (
                <ul className="mb-3 space-y-1">
                  {attrs.map((a) => (
                    <li key={a.key} className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 text-sm">
                      <span><strong>{a.key}</strong>: {a.value}</span>
                      <button type="button" onClick={() => removeAttribute(a.key)} className="text-red-600 hover:underline">Remove</button>
                    </li>
                  ))}
                </ul>
              )}

              <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 flex gap-2">
                <input type="text" placeholder="Attribute Key (e.g. Voltage, GSM, Material)" value={attrKey} onChange={(e) => setAttrKey(e.target.value)} className="flex-1 p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
                <input type="text" placeholder="Value (e.g. 220V, 400g, Steel)" value={attrValue} onChange={(e) => setAttrValue(e.target.value)} className="flex-1 p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
                <button type="button" onClick={addAttribute} className="bg-gray-200 dark:bg-gray-700 px-4 py-2 rounded text-sm hover:bg-gray-300 transition-colors">Add</button>
              </div>
            </div>

            <div className="flex justify-end gap-2">
              <button type="button" onClick={resetForm} className="px-4 py-2 text-gray-600 hover:text-gray-900">Cancel</button>
              <button type="submit" disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
                {saving ? 'Saving...' : editingId ? 'Update Item' : 'Save Item'}
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden border border-gray-200 dark:border-gray-700">
        <table className="min-w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
            <tr>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">SKU</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Item Name</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Status</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Attributes</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {loading ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={5}>Loading items...</td></tr>
            ) : items.length === 0 ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={5}>No items found. Create one to begin.</td></tr>
            ) : items.map((item) => (
              <tr key={item.id}>
                <td className="px-6 py-4 font-mono">{item.sku}</td>
                <td className="px-6 py-4 font-medium">{item.name}</td>
                <td className="px-6 py-4">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
                    {item.status}
                  </span>
                </td>
                <td className="px-6 py-4 text-gray-500">{Object.keys(item.attributes || {}).length} field(s)</td>
                <td className="px-6 py-4 space-x-3">
                  <button onClick={() => handleEdit(item)} className="text-blue-600 hover:underline">Edit</button>
                  <button onClick={() => handleDelete(item.id)} className="text-red-600 hover:underline">Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
