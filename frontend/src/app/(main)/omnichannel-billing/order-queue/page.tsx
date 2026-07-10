'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import apiClient, { isApiError } from '@/lib/apiClient';

interface Channel {
  id: string;
  platform_name: string;
}

interface OrderMapping {
  id: string;
  channel_id: string;
  external_order_id: string;
  sync_status: string;
}

const CHANNELS_BASE = '/api/v1/omnichannel-billing/channels';

export default function OrderQueuePage() {
  const [mappings, setMappings] = useState<OrderMapping[]>([]);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const [channelId, setChannelId] = useState('');
  const [externalOrderId, setExternalOrderId] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([apiClient.get(`${CHANNELS_BASE}/orders`), apiClient.get(`${CHANNELS_BASE}/channels`)])
      .then(([mapRes, chanRes]) => {
        setMappings(mapRes.data.items || []);
        setChannels(chanRes.data.items || []);
      })
      .catch(() => setError('Failed to load order queue'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const channelName = (id: string) => channels.find((c) => c.id === id)?.platform_name || id;

  const resetForm = () => {
    setShowForm(false);
    setChannelId('');
    setExternalOrderId('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      await apiClient.post(`${CHANNELS_BASE}/orders`, { channel_id: channelId, external_order_id: externalOrderId });
      resetForm();
      load();
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to sync order');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/omnichannel-billing/analytics/dashboard" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Billing Dashboard</Link>
          <h1 className="text-2xl font-bold">Omnichannel Order Queue</h1>
          <p className="text-gray-600 dark:text-gray-400">Orders synced from Web, Mobile, Social, and Marketplaces.</p>
        </div>
        <button onClick={() => (showForm ? resetForm() : setShowForm(true))} className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700 transition-colors">
          {showForm ? 'Cancel' : 'Sync Order'}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      {channels.length === 0 && !loading && (
        <p className="text-sm text-yellow-600 mb-4">No sales channels configured yet - configure one before syncing orders.</p>
      )}

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md mb-8 border border-gray-200 dark:border-gray-700 space-y-4">
          <h2 className="text-lg font-semibold">Sync External Order</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Channel</label>
              <select required value={channelId} onChange={(e) => setChannelId(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600">
                <option value="">- Select -</option>
                {channels.map((c) => (<option key={c.id} value={c.id}>{c.platform_name}</option>))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">External Order ID</label>
              <input type="text" required value={externalOrderId} onChange={(e) => setExternalOrderId(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={resetForm} className="px-4 py-2 text-gray-600 hover:text-gray-900">Cancel</button>
            <button type="submit" disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Syncing...' : 'Sync'}
            </button>
          </div>
        </form>
      )}

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden border border-gray-200 dark:border-gray-700">
        <table className="min-w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
            <tr>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Order Ref</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Channel</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Sync Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {loading ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={3}>Loading order queue...</td></tr>
            ) : mappings.length === 0 ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={3}>No orders in queue.</td></tr>
            ) : mappings.map((m) => (
              <tr key={m.id}>
                <td className="px-6 py-4 font-mono">{m.external_order_id}</td>
                <td className="px-6 py-4">{channelName(m.channel_id)}</td>
                <td className="px-6 py-4">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
                    {m.sync_status}
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
