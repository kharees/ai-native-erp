'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import apiClient, { isApiError } from '@/lib/apiClient';

interface Item {
  id: string;
  name: string;
  sku: string;
}

interface Warehouse {
  id: string;
  name: string;
}

interface LedgerEntry {
  id: string;
  item_id: string;
  warehouse_id: string;
  movement_quantity: number;
  reference_type: string;
  created_at: string;
}

const STOCK_TXN_BASE = '/api/v1/universal-warehousing/stock/transactions';
const ITEMS_BASE = '/api/v1/universal-inventory/items';
const WAREHOUSES_BASE = '/api/v1/universal-warehousing/warehouses';
const LEDGER_BASE = '/api/v1/universal-ledger/';

export default function StockMovementPage() {
  const [items, setItems] = useState<Item[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [entries, setEntries] = useState<LedgerEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const [txnType, setTxnType] = useState('IN');
  const [itemId, setItemId] = useState('');
  const [warehouseId, setWarehouseId] = useState('');
  const [quantity, setQuantity] = useState('');
  const [metaKey, setMetaKey] = useState('');
  const [metaValue, setMetaValue] = useState('');
  const [metadata, setMetadata] = useState<{ key: string; value: string }[]>([]);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([
      apiClient.get(ITEMS_BASE),
      apiClient.get(WAREHOUSES_BASE),
      apiClient.get(LEDGER_BASE),
    ])
      .then(([itemsRes, whRes, ledgerRes]) => {
        setItems(itemsRes.data.items || []);
        setWarehouses(whRes.data.items || []);
        setEntries(ledgerRes.data.items || []);
      })
      .catch(() => setError('Failed to load stock data'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const itemLabel = (id: string) => items.find((i) => i.id === id)?.name || id;
  const warehouseLabel = (id: string) => warehouses.find((w) => w.id === id)?.name || id;

  const addMetadata = () => {
    if (!metaKey.trim()) return;
    setMetadata((prev) => [...prev, { key: metaKey.trim(), value: metaValue.trim() }]);
    setMetaKey('');
    setMetaValue('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      await apiClient.post(STOCK_TXN_BASE, {
        item_id: itemId,
        warehouse_id: warehouseId,
        transaction_type: txnType,
        reference_type: txnType === 'IN' ? 'GRN' : txnType === 'OUT' ? 'GI' : txnType,
        quantity: parseFloat(quantity),
        metadata: Object.fromEntries(metadata.map((m) => [m.key, m.value])),
      });
      setItemId('');
      setWarehouseId('');
      setQuantity('');
      setMetadata([]);
      load();
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to execute movement');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div className="flex justify-between items-center">
        <div>
          <Link href="/universal-inventory" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Inventory Dashboard</Link>
          <h1 className="text-3xl font-bold">Universal Stock Engine</h1>
          <p className="text-gray-500 text-sm mt-1">Execute multi-warehouse inventory movements.</p>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md border border-gray-200 dark:border-gray-700">
        <h2 className="text-lg font-semibold mb-4 border-b pb-2 dark:border-gray-700">New Transaction</h2>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Transaction Type</label>
              <select
                value={txnType}
                onChange={(e) => setTxnType(e.target.value)}
                className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600"
              >
                <option value="IN">Stock In (GRN)</option>
                <option value="OUT">Stock Out (GI)</option>
                <option value="TRANSFER">Transfer</option>
                <option value="ADJUST">Adjustment</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Item</label>
              <select required value={itemId} onChange={(e) => setItemId(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600">
                <option value="">Select Item...</option>
                {items.map((i) => (
                  <option key={i.id} value={i.id}>{i.name} ({i.sku})</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Warehouse</label>
              <select required value={warehouseId} onChange={(e) => setWarehouseId(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600">
                <option value="">Select Warehouse...</option>
                {warehouses.map((w) => (
                  <option key={w.id} value={w.id}>{w.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Quantity</label>
              <input type="number" required min="0.0001" step="0.0001" value={quantity} onChange={(e) => setQuantity(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
            </div>
          </div>

          <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
            <h3 className="text-md font-medium mb-2">Dynamic Transaction Metadata</h3>
            <p className="text-xs text-gray-500 mb-4">Attach schema-less metadata directly to this movement (e.g., Driver Name, Vehicle Number, Supplier Batch ID).</p>

            {metadata.length > 0 && (
              <ul className="mb-3 space-y-1">
                {metadata.map((m) => (
                  <li key={m.key} className="text-sm p-2 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700">
                    <strong>{m.key}</strong>: {m.value}
                  </li>
                ))}
              </ul>
            )}

            <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 flex gap-2">
              <input type="text" placeholder="Metadata Key" value={metaKey} onChange={(e) => setMetaKey(e.target.value)} className="flex-1 p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
              <input type="text" placeholder="Value" value={metaValue} onChange={(e) => setMetaValue(e.target.value)} className="flex-1 p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
              <button type="button" onClick={addMetadata} className="bg-gray-200 dark:bg-gray-700 px-4 py-2 rounded text-sm hover:bg-gray-300 transition-colors">Add</button>
            </div>
          </div>

          <div className="flex justify-end pt-4">
            <button type="submit" disabled={saving} className="px-6 py-2 bg-green-600 text-white rounded hover:bg-green-700 font-medium disabled:opacity-50">
              {saving ? 'Executing...' : 'Execute Movement'}
            </button>
          </div>
        </form>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden border border-gray-200 dark:border-gray-700">
        <h3 className="p-4 font-semibold border-b dark:border-gray-700">Recent Transactions</h3>
        <table className="min-w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
            <tr>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Timestamp</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Type</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Item</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Qty</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Warehouse</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {loading ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={5}>Loading transactions...</td></tr>
            ) : entries.length === 0 ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={5}>No transactions recorded.</td></tr>
            ) : entries.map((e) => (
              <tr key={e.id}>
                <td className="px-6 py-4 text-gray-500">{new Date(e.created_at).toLocaleString()}</td>
                <td className="px-6 py-4">{e.reference_type}</td>
                <td className="px-6 py-4">{itemLabel(e.item_id)}</td>
                <td className="px-6 py-4">{e.movement_quantity > 0 ? `+${e.movement_quantity}` : e.movement_quantity}</td>
                <td className="px-6 py-4">{warehouseLabel(e.warehouse_id)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
