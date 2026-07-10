'use client';
import React, { useState, useEffect, useCallback } from 'react';
import apiClient, { isApiError } from '@/lib/apiClient';

interface AuditLog {
  id: string;
  user_id: string | null;
  action_category: string;
  action_type: string;
  action_source: string;
  resource_id: string | null;
  old_values: Record<string, unknown> | null;
  new_values: Record<string, unknown> | null;
  ip_address: string | null;
  user_agent: string | null;
  correlation_id: string | null;
  created_at: string;
}

export default function AuditDashboardPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [category, setCategory] = useState('');
  const [search, setSearch] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    setError('');
    const params: Record<string, string> = {};
    if (category) params.action_category = category;
    apiClient
      .get('/api/v1/audit/', { params })
      .then((res) => setLogs(res.data || []))
      .catch((err) => setError(isApiError(err) ? err.message : 'Failed to load audit logs'))
      .finally(() => setLoading(false));
  }, [category]);

  useEffect(() => {
    load();
  }, [load]);

  const filteredLogs = logs.filter((log) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      (log.resource_id || '').toLowerCase().includes(q) ||
      (log.ip_address || '').toLowerCase().includes(q) ||
      log.action_type.toLowerCase().includes(q)
    );
  });

  return (
    <div className="min-h-screen bg-gray-50/50 dark:bg-[#0a0a0a] p-8">
      <div className="max-w-7xl mx-auto space-y-8">

        <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white">Audit & Activity Log</h1>
            <p className="text-gray-500 dark:text-gray-400 mt-1">
              Immutable enterprise ledger of systemic actions and modifications.
            </p>
          </div>
        </header>

        {error && (
          <div className="p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="px-4 py-2.5 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg text-sm text-gray-700 dark:text-gray-300 focus:ring-2 focus:ring-blue-500 outline-none"
          >
            <option value="">Category: All</option>
            <option value="AUTH">AUTH</option>
            <option value="RBAC">RBAC</option>
            <option value="ERP_CONNECTOR">ERP_CONNECTOR</option>
            <option value="MIGRATION">MIGRATION</option>
            <option value="MIGRATION_EXECUTION">MIGRATION_EXECUTION</option>
            <option value="MIGRATION_AI">MIGRATION_AI</option>
          </select>
          <div className="relative md:col-span-3">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full px-4 py-2.5 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition-all text-sm"
              placeholder="Search by resource ID, IP, or action..."
            />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl shadow-sm overflow-hidden flex flex-col md:flex-row min-h-[500px]">
          <div className={`w-full ${selectedLog ? 'md:w-1/2 border-r border-gray-200 dark:border-gray-800' : ''} transition-all duration-300`}>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-800">
                    <th className="px-6 py-4 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Timestamp</th>
                    <th className="px-6 py-4 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">IP</th>
                    <th className="px-6 py-4 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                  {loading ? (
                    <tr><td colSpan={3} className="px-6 py-8 text-center text-sm text-gray-500">Loading audit logs...</td></tr>
                  ) : filteredLogs.length === 0 ? (
                    <tr><td colSpan={3} className="px-6 py-8 text-center text-sm text-gray-500">No audit logs found.</td></tr>
                  ) : filteredLogs.map((log) => (
                    <tr
                      key={log.id}
                      onClick={() => setSelectedLog(log)}
                      className={`cursor-pointer transition-colors ${selectedLog?.id === log.id ? 'bg-blue-50 dark:bg-blue-900/10' : 'hover:bg-gray-50 dark:hover:bg-gray-800/50'}`}
                    >
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {new Date(log.created_at).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {log.ip_address || '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <span className="inline-flex px-2 py-0.5 rounded text-[10px] font-bold bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400 border border-gray-200 dark:border-gray-700">
                            {log.action_category}
                          </span>
                          <span className="text-sm font-medium text-gray-900 dark:text-gray-300">{log.action_type}</span>
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400 mt-1 truncate max-w-[200px]">
                          {log.resource_id || ''}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {selectedLog && (
            <div className="w-full md:w-1/2 bg-gray-50/30 dark:bg-[#0c0c0c] p-6 overflow-y-auto">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Log Details</h3>
                <button onClick={() => setSelectedLog(null)} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
                </button>
              </div>

              <div className="space-y-6">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Log ID</div>
                    <div className="text-sm font-mono text-gray-900 dark:text-gray-300">{selectedLog.id}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Source</div>
                    <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">
                      {selectedLog.action_source}
                    </span>
                  </div>
                </div>

                {(selectedLog.old_values || selectedLog.new_values) && (
                  <div className="border-t border-gray-200 dark:border-gray-800 pt-4">
                    <div className="text-xs text-gray-500 dark:text-gray-400 mb-3 uppercase tracking-wider font-semibold">Delta Tracking</div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-red-50 dark:bg-red-900/10 border border-red-100 dark:border-red-900/30 rounded-lg p-3">
                        <div className="text-xs font-semibold text-red-600 dark:text-red-400 mb-2">Old Value</div>
                        <pre className="text-[10px] sm:text-xs text-red-800 dark:text-red-300 font-mono overflow-x-auto">
{JSON.stringify(selectedLog.old_values || {}, null, 2)}
                        </pre>
                      </div>
                      <div className="bg-emerald-50 dark:bg-emerald-900/10 border border-emerald-100 dark:border-emerald-900/30 rounded-lg p-3">
                        <div className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 mb-2">New Value</div>
                        <pre className="text-[10px] sm:text-xs text-emerald-800 dark:text-emerald-300 font-mono overflow-x-auto">
{JSON.stringify(selectedLog.new_values || {}, null, 2)}
                        </pre>
                      </div>
                    </div>
                  </div>
                )}

                <div className="border-t border-gray-200 dark:border-gray-800 pt-4">
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-3 uppercase tracking-wider font-semibold">Network Trace</div>
                  <pre className="text-xs text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 p-3 rounded-lg overflow-x-auto font-mono">
{`User-Agent: ${selectedLog.user_agent || 'unknown'}
IP: ${selectedLog.ip_address || 'unknown'}
Correlation-ID: ${selectedLog.correlation_id || 'none'}`}
                  </pre>
                </div>
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
