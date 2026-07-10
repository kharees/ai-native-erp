'use client';
import React, { useState, useEffect, useCallback } from 'react';
import apiClient, { isApiError } from '@/lib/apiClient';

interface TenantSession {
  id: string;
  device_fingerprint: string | null;
  ip_address: string | null;
  browser: string | null;
  os: string | null;
  is_active: boolean;
  last_active_at: string;
  expires_at: string;
}

interface TenantDevice {
  id: string;
  device_fingerprint: string;
  browser: string | null;
  os: string | null;
  last_ip_address: string | null;
  is_trusted: boolean;
  last_seen_at: string;
}

export default function SessionManagementPage() {
  const [activeTab, setActiveTab] = useState<'sessions' | 'devices'>('sessions');
  const [sessions, setSessions] = useState<TenantSession[]>([]);
  const [devices, setDevices] = useState<TenantDevice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError('');
    Promise.all([
      apiClient.get('/api/v1/sessions/me'),
      apiClient.get('/api/v1/sessions/devices'),
    ])
      .then(([sessRes, devRes]) => {
        setSessions(sessRes.data || []);
        setDevices(devRes.data || []);
      })
      .catch((err) => setError(isApiError(err) ? err.message : 'Failed to load sessions'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleRevoke = async (id: string) => {
    setActionLoading(true);
    setError('');
    try {
      await apiClient.delete(`/api/v1/sessions/${id}`);
      load();
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to revoke session');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRevokeAll = async () => {
    setActionLoading(true);
    setError('');
    try {
      await apiClient.delete('/api/v1/sessions/me/all');
      load();
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to revoke sessions');
    } finally {
      setActionLoading(false);
    }
  };

  const handleTrustDevice = async (id: string) => {
    setActionLoading(true);
    setError('');
    try {
      await apiClient.patch(`/api/v1/sessions/devices/${id}/trust`);
      load();
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to trust device');
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50/50 dark:bg-[#0a0a0a] p-8">
      <div className="max-w-6xl mx-auto space-y-8">

        <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white">Active Sessions</h1>
            <p className="text-gray-500 dark:text-gray-400 mt-1">
              Manage your signed-in devices and active web sessions.
            </p>
          </div>
          <button
            onClick={handleRevokeAll}
            disabled={actionLoading}
            className="px-4 py-2 bg-red-50 text-red-600 dark:bg-red-500/10 dark:text-red-400 border border-red-200 dark:border-red-900/50 hover:bg-red-100 dark:hover:bg-red-500/20 rounded-lg text-sm font-medium transition-colors shadow-sm flex items-center gap-2 disabled:opacity-50"
          >
            Sign out all other sessions
          </button>
        </header>

        {error && (
          <div className="p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
        )}

        <div className="border-b border-gray-200 dark:border-gray-800">
          <nav className="-mb-px flex space-x-8">
            {(['sessions', 'devices'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`whitespace-nowrap pb-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === tab
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                }`}
              >
                {tab === 'sessions' ? 'Active Sessions' : 'Trusted Devices'}
              </button>
            ))}
          </nav>
        </div>

        {activeTab === 'sessions' && (
          <div className="space-y-4">
            {loading ? (
              <p className="text-sm text-gray-500">Loading sessions...</p>
            ) : sessions.length === 0 ? (
              <p className="text-sm text-gray-500">No active sessions found.</p>
            ) : sessions.map((session) => (
              <div key={session.id} className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <h3 className="text-base font-semibold text-gray-900 dark:text-white">
                    {session.browser || 'Unknown Browser'} on {session.os || 'Unknown OS'}
                  </h3>
                  <div className="text-sm text-gray-500 dark:text-gray-400 mt-1 flex flex-wrap gap-x-4 gap-y-1">
                    <span>IP: {session.ip_address || 'unknown'}</span>
                    <span>Expires: {new Date(session.expires_at).toLocaleString()}</span>
                  </div>
                  <div className="text-xs text-gray-400 dark:text-gray-500 mt-2">
                    Last active: {new Date(session.last_active_at).toLocaleString()}
                  </div>
                </div>
                <button
                  onClick={() => handleRevoke(session.id)}
                  disabled={actionLoading}
                  className="self-start md:self-center px-4 py-2 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-lg text-sm font-medium transition-colors text-gray-700 dark:text-gray-300 disabled:opacity-50"
                >
                  Revoke Session
                </button>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'devices' && (
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr>
                    <th className="px-6 py-4 bg-gray-50 dark:bg-gray-800/30 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider border-b border-gray-200 dark:border-gray-800">Device</th>
                    <th className="px-6 py-4 bg-gray-50 dark:bg-gray-800/30 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider border-b border-gray-200 dark:border-gray-800">Status</th>
                    <th className="px-6 py-4 bg-gray-50 dark:bg-gray-800/30 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider border-b border-gray-200 dark:border-gray-800">Last Seen</th>
                    <th className="px-6 py-4 bg-gray-50 dark:bg-gray-800/30 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider border-b border-gray-200 dark:border-gray-800">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                  {loading ? (
                    <tr><td colSpan={4} className="px-6 py-8 text-center text-sm text-gray-500">Loading devices...</td></tr>
                  ) : devices.length === 0 ? (
                    <tr><td colSpan={4} className="px-6 py-8 text-center text-sm text-gray-500">No known devices found.</td></tr>
                  ) : devices.map(device => (
                    <tr key={device.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/20 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900 dark:text-gray-200">{device.browser || 'Unknown'} / {device.os || 'Unknown'}</div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">{device.last_ip_address || ''}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {device.is_trusted ? (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-900/50">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                            Trusted
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-gray-50 text-gray-600 dark:bg-gray-800 dark:text-gray-400 border border-gray-200 dark:border-gray-700">
                            Untrusted
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {new Date(device.last_seen_at).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {!device.is_trusted && (
                          <button
                            onClick={() => handleTrustDevice(device.id)}
                            disabled={actionLoading}
                            className="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 text-sm font-medium disabled:opacity-50"
                          >
                            Trust Device
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
