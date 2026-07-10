'use client';

import { useEffect, useState, useCallback } from 'react';
import apiClient, { isApiError } from '@/lib/apiClient';
import { useAuthStore } from '@/store/authStore';

interface Vendor {
  id: string;
  name: string;
  email: string | null;
  outstanding_amount: number;
}

interface Bill {
  id: string;
  vendor_id: string;
  bill_number: string;
  amount: number;
  due_date: string;
  status: string;
}

const BASE = '/api/v1/finance-ar-ap';

function daysUntil(dateStr: string): number {
  return Math.ceil((new Date(dateStr).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
}

export default function AccountsPayablePage() {
  const tenantId = useAuthStore((s) => s.user?.tenant_id);
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [bills, setBills] = useState<Bill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [formMode, setFormMode] = useState<'none' | 'vendor' | 'bill'>('none');

  const [vendorName, setVendorName] = useState('');
  const [vendorEmail, setVendorEmail] = useState('');

  const [billVendorId, setBillVendorId] = useState('');
  const [billNumber, setBillNumber] = useState('');
  const [billAmount, setBillAmount] = useState('');
  const [billDueDate, setBillDueDate] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([apiClient.get(`${BASE}/ap/vendors`), apiClient.get(`${BASE}/ap/bills`)])
      .then(([vendorRes, billRes]) => {
        setVendors(vendorRes.data || []);
        setBills(billRes.data || []);
      })
      .catch(() => setError('Failed to load accounts payable'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const vendorName_ = (id: string) => vendors.find((v) => v.id === id)?.name || id;

  const resetForm = () => {
    setFormMode('none');
    setVendorName('');
    setVendorEmail('');
    setBillVendorId('');
    setBillNumber('');
    setBillAmount('');
    setBillDueDate('');
  };

  const handleCreateVendor = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tenantId) return;
    setSaving(true);
    setError('');
    try {
      await apiClient.post(`${BASE}/ap/vendors`, { tenant_id: tenantId, name: vendorName, email: vendorEmail || null });
      resetForm();
      load();
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to create vendor');
    } finally {
      setSaving(false);
    }
  };

  const handleCreateBill = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tenantId) return;
    setSaving(true);
    setError('');
    try {
      await apiClient.post(`${BASE}/ap/bills`, {
        tenant_id: tenantId,
        vendor_id: billVendorId,
        bill_number: billNumber,
        amount: parseFloat(billAmount),
        due_date: new Date(billDueDate).toISOString(),
      });
      resetForm();
      load();
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to record bill');
    } finally {
      setSaving(false);
    }
  };

  const totalOutstanding = vendors.reduce((sum, v) => sum + Number(v.outstanding_amount), 0);
  const dueWithin7 = bills.filter((b) => daysUntil(b.due_date) <= 7 && daysUntil(b.due_date) >= 0).reduce((sum, b) => sum + Number(b.amount), 0);
  const paidBillsTotal = bills.filter((b) => b.status === 'PAID').reduce((sum, b) => sum + Number(b.amount), 0);

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Accounts Payable (AP)</h1>
        <div className="flex space-x-2">
          <button onClick={() => setFormMode(formMode === 'bill' ? 'none' : 'bill')} className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700">
            {formMode === 'bill' ? 'Cancel' : 'Record Bill'}
          </button>
          <button onClick={() => setFormMode(formMode === 'vendor' ? 'none' : 'vendor')} className="bg-gray-100 text-gray-700 px-4 py-2 rounded shadow hover:bg-gray-200">
            {formMode === 'vendor' ? 'Cancel' : 'New Vendor'}
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-white p-4 shadow rounded-lg border-l-4 border-red-500">
          <p className="text-sm text-gray-500 font-medium">Total Outstanding</p>
          <p className="text-2xl font-bold">${totalOutstanding.toFixed(2)}</p>
        </div>
        <div className="bg-white p-4 shadow rounded-lg border-l-4 border-yellow-500">
          <p className="text-sm text-gray-500 font-medium">Due in 7 Days</p>
          <p className="text-2xl font-bold text-yellow-600">${dueWithin7.toFixed(2)}</p>
        </div>
        <div className="bg-white p-4 shadow rounded-lg border-l-4 border-green-500">
          <p className="text-sm text-gray-500 font-medium">Paid Bills Total</p>
          <p className="text-2xl font-bold">${paidBillsTotal.toFixed(2)}</p>
        </div>
      </div>

      {formMode === 'vendor' && (
        <form onSubmit={handleCreateVendor} className="bg-white shadow rounded-lg p-6 mb-6 space-y-4">
          <h2 className="text-lg font-semibold">New Vendor</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Name</label>
              <input type="text" required value={vendorName} onChange={(e) => setVendorName(e.target.value)} className="w-full p-2 border rounded" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Email</label>
              <input type="email" value={vendorEmail} onChange={(e) => setVendorEmail(e.target.value)} className="w-full p-2 border rounded" />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={resetForm} className="px-4 py-2 text-gray-600 hover:text-gray-900">Cancel</button>
            <button type="submit" disabled={saving || !tenantId} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Saving...' : 'Save Vendor'}
            </button>
          </div>
        </form>
      )}

      {formMode === 'bill' && (
        <form onSubmit={handleCreateBill} className="bg-white shadow rounded-lg p-6 mb-6 space-y-4">
          <h2 className="text-lg font-semibold">Record New Bill</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Vendor</label>
              <select required value={billVendorId} onChange={(e) => setBillVendorId(e.target.value)} className="w-full p-2 border rounded">
                <option value="">- Select -</option>
                {vendors.map((v) => (
                  <option key={v.id} value={v.id}>{v.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Bill Number</label>
              <input type="text" required value={billNumber} onChange={(e) => setBillNumber(e.target.value)} className="w-full p-2 border rounded" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Amount</label>
              <input type="number" step="0.01" required value={billAmount} onChange={(e) => setBillAmount(e.target.value)} className="w-full p-2 border rounded" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Due Date</label>
              <input type="date" required value={billDueDate} onChange={(e) => setBillDueDate(e.target.value)} className="w-full p-2 border rounded" />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={resetForm} className="px-4 py-2 text-gray-600 hover:text-gray-900">Cancel</button>
            <button type="submit" disabled={saving || !tenantId} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Saving...' : 'Save Bill'}
            </button>
          </div>
        </form>
      )}

      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="px-6 py-3 bg-gray-50 border-b font-semibold text-sm">Bills</div>
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Vendor</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Bill Number</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Amount</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Due Date</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {loading ? (
              <tr><td colSpan={5} className="px-6 py-4 text-center">Loading...</td></tr>
            ) : bills.length === 0 ? (
              <tr><td colSpan={5} className="px-6 py-4 text-center text-gray-500">No bills recorded.</td></tr>
            ) : bills.map((b) => (
              <tr key={b.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-blue-600">{vendorName_(b.vendor_id)}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">{b.bill_number}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium">${Number(b.amount).toFixed(2)}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right">{new Date(b.due_date).toLocaleDateString()}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                    b.status === 'PAID' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                  }`}>{b.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
