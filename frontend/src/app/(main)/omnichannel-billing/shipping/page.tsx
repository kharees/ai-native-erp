'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import apiClient, { isApiError } from '@/lib/apiClient';

interface Courier {
  id: string;
  courier_name: string;
}

interface SalesOrder {
  id: string;
  order_number: string;
}

interface Dispatch {
  id: string;
  sales_order_id: string;
  courier_id: string | null;
  tracking_number: string | null;
  dispatch_status: string;
}

const SHIPPING_BASE = '/api/v1/omnichannel-billing/shipping';

export default function ShippingPage() {
  const [dispatches, setDispatches] = useState<Dispatch[]>([]);
  const [couriers, setCouriers] = useState<Courier[]>([]);
  const [orders, setOrders] = useState<SalesOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [showCourierForm, setShowCourierForm] = useState(false);

  const [orderId, setOrderId] = useState('');
  const [courierId, setCourierId] = useState('');
  const [trackingNumber, setTrackingNumber] = useState('');
  const [newCourierName, setNewCourierName] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([
      apiClient.get(`${SHIPPING_BASE}/dispatches`),
      apiClient.get(`${SHIPPING_BASE}/couriers`),
      apiClient.get('/api/v1/omnichannel-billing/sales/orders'),
    ])
      .then(([dispatchRes, courierRes, orderRes]) => {
        setDispatches(dispatchRes.data.items || []);
        setCouriers(courierRes.data.items || []);
        setOrders(orderRes.data.items || []);
      })
      .catch(() => setError('Failed to load shipping data'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const courierName = (id: string | null) => couriers.find((c) => c.id === id)?.courier_name || '-';
  const orderNumber = (id: string) => orders.find((o) => o.id === id)?.order_number || id;

  const resetForm = () => {
    setShowForm(false);
    setOrderId('');
    setCourierId('');
    setTrackingNumber('');
  };

  const handleCreateCourier = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      await apiClient.post(`${SHIPPING_BASE}/couriers`, { courier_name: newCourierName });
      setNewCourierName('');
      setShowCourierForm(false);
      load();
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to add courier');
    } finally {
      setSaving(false);
    }
  };

  const handleDispatch = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      await apiClient.post(`${SHIPPING_BASE}/dispatches`, {
        sales_order_id: orderId,
        courier_id: courierId || null,
        tracking_number: trackingNumber || null,
      });
      resetForm();
      load();
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to dispatch order');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/omnichannel-billing/analytics/dashboard" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Billing Dashboard</Link>
          <h1 className="text-2xl font-bold">Shipping & Logistics Manager</h1>
          <p className="text-gray-600 dark:text-gray-400">Track couriers, AWBs, and delivery statuses.</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowCourierForm(!showCourierForm)} className="bg-gray-100 text-gray-700 px-4 py-2 rounded shadow hover:bg-gray-200 transition-colors">
            {showCourierForm ? 'Cancel' : 'Add Courier'}
          </button>
          <button onClick={() => (showForm ? resetForm() : setShowForm(true))} className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700 transition-colors">
            {showForm ? 'Cancel' : 'Dispatch Order'}
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      {showCourierForm && (
        <form onSubmit={handleCreateCourier} className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md mb-8 border border-gray-200 dark:border-gray-700 flex gap-4 items-end">
          <div className="flex-1">
            <label className="block text-sm font-medium mb-1">Courier Name</label>
            <input type="text" required value={newCourierName} onChange={(e) => setNewCourierName(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
          </div>
          <button type="submit" disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">Save</button>
        </form>
      )}

      {showForm && (
        <form onSubmit={handleDispatch} className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md mb-8 border border-gray-200 dark:border-gray-700 space-y-4">
          <h2 className="text-lg font-semibold">Dispatch Sales Order</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Sales Order</label>
              <select required value={orderId} onChange={(e) => setOrderId(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600">
                <option value="">- Select -</option>
                {orders.map((o) => (<option key={o.id} value={o.id}>{o.order_number}</option>))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Courier</label>
              <select value={courierId} onChange={(e) => setCourierId(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600">
                <option value="">- None -</option>
                {couriers.map((c) => (<option key={c.id} value={c.id}>{c.courier_name}</option>))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Tracking Number</label>
              <input type="text" value={trackingNumber} onChange={(e) => setTrackingNumber(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600" />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={resetForm} className="px-4 py-2 text-gray-600 hover:text-gray-900">Cancel</button>
            <button type="submit" disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Dispatching...' : 'Dispatch'}
            </button>
          </div>
        </form>
      )}

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden border border-gray-200 dark:border-gray-700">
        <table className="min-w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
            <tr>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Order</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Courier</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">AWB Tracking No</th>
              <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Dispatch Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {loading ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={4}>Loading dispatches...</td></tr>
            ) : dispatches.length === 0 ? (
              <tr><td className="px-6 py-4 text-center text-gray-500" colSpan={4}>No dispatched orders found.</td></tr>
            ) : dispatches.map((d) => (
              <tr key={d.id}>
                <td className="px-6 py-4">{orderNumber(d.sales_order_id)}</td>
                <td className="px-6 py-4">{courierName(d.courier_id)}</td>
                <td className="px-6 py-4 font-mono">{d.tracking_number || '-'}</td>
                <td className="px-6 py-4">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
                    {d.dispatch_status}
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
