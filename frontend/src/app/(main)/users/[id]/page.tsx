'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import apiClient from '@/lib/apiClient';

interface UserProfile {
  id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  phone: string | null;
  designation: string | null;
  employee_code: string | null;
  department_id: string | null;
  is_active: boolean;
  status: string;
  role: string;
  timezone: string;
  locale: string;
  created_at: string;
  updated_at: string;
}

export default function UserDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params?.id as string;
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    designation: '',
    phone: '',
    employee_code: '',
  });

  useEffect(() => {
    if (!id) return;
    apiClient.get(`/api/v1/users/${id}`)
      .then(res => {
        setUser(res.data);
        setFormData({
          first_name: res.data.first_name || '',
          last_name: res.data.last_name || '',
          designation: res.data.designation || '',
          phone: res.data.phone || '',
          employee_code: res.data.employee_code || '',
        });
      })
      .catch(() => setError('Failed to load user profile'))
      .finally(() => setLoading(false));
  }, [id]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      await apiClient.patch(`/api/v1/users/${id}`, formData);
      router.push('/users');
    } catch {
      setError('Failed to update user profile');
      setSaving(false);
    }
  };

  if (loading) return (
    <div className="min-h-screen bg-gray-50/50 dark:bg-[#0a0a0a] p-8 flex items-center justify-center">
      <div className="text-gray-500">Loading user profile...</div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50/50 dark:bg-[#0a0a0a] p-8">
      <div className="max-w-3xl mx-auto space-y-8">
        <header>
          <Link href="/users" className="text-blue-600 hover:underline text-sm mb-2 block">← Back to Users</Link>
          <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white">
            Edit User Profile
          </h1>
          {user && (
            <p className="text-gray-500 dark:text-gray-400 mt-1">{user.email}</p>
          )}
        </header>

        {error && (
          <div className="p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
        )}

        <form onSubmit={handleSubmit} className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl shadow-sm overflow-hidden">
          <div className="p-6 space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">First Name</label>
                <input
                  type="text"
                  value={formData.first_name}
                  onChange={e => setFormData(prev => ({ ...prev, first_name: e.target.value }))}
                  className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Last Name</label>
                <input
                  type="text"
                  value={formData.last_name}
                  onChange={e => setFormData(prev => ({ ...prev, last_name: e.target.value }))}
                  className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Phone</label>
                <input
                  type="tel"
                  value={formData.phone}
                  onChange={e => setFormData(prev => ({ ...prev, phone: e.target.value }))}
                  className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Employee Code</label>
                <input
                  type="text"
                  value={formData.employee_code}
                  onChange={e => setFormData(prev => ({ ...prev, employee_code: e.target.value }))}
                  className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Designation</label>
                <input
                  type="text"
                  value={formData.designation}
                  onChange={e => setFormData(prev => ({ ...prev, designation: e.target.value }))}
                  className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            {user && (
              <div className="pt-4 border-t border-gray-200 dark:border-gray-800">
                <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Account Status</h3>
                <div className="flex items-center gap-4">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${
                    user.is_active
                      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                      : 'bg-red-50 text-red-700 border-red-200'
                  }`}>
                    {user.is_active ? 'Active' : 'Suspended'}
                  </span>
                  <span className="text-sm text-gray-500">Role: {user.role}</span>
                </div>
              </div>
            )}
          </div>

          <div className="p-4 bg-gray-50 dark:bg-gray-800/30 border-t border-gray-200 dark:border-gray-800 flex justify-end gap-3">
            <button
              type="button"
              onClick={() => router.back()}
              className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              disabled={saving}
              type="submit"
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors shadow-sm disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
