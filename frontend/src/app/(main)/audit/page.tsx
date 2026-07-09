'use client';
import React, { useState } from 'react';

interface AuditLog {
  id: string;
  timestamp: string;
  actor: string;
  category: string;
  action: string;
  resource: string;
  ip: string;
  status: string;
}

export default function AuditDashboardPage() {
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);

  const dummyLogs = [
    {
      id: "LOG-001",
      timestamp: "2026-07-04 14:30:22 UTC",
      actor: "Jane Smith (Admin)",
      category: "RBAC",
      action: "ROLE_ASSIGNED",
      resource: "User: john.doe@example.com",
      ip: "192.168.1.105",
      status: "SUCCESS"
    },
    {
      id: "LOG-002",
      timestamp: "2026-07-04 14:15:10 UTC",
      actor: "John Doe",
      category: "AUTH",
      action: "LOGIN_SUCCESS",
      resource: "Session: auth-token",
      ip: "10.0.0.55",
      status: "SUCCESS"
    },
    {
      id: "LOG-003",
      timestamp: "2026-07-04 13:45:00 UTC",
      actor: "Jane Smith (Admin)",
      category: "INVENTORY",
      action: "ITEM_UPDATED",
      resource: "SKU: WH-10293",
      ip: "192.168.1.105",
      status: "SUCCESS"
    }
  ];

  return (
    <div className="min-h-screen bg-gray-50/50 dark:bg-[#0a0a0a] p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Header Section */}
        <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white">Audit & Activity Log</h1>
            <p className="text-gray-500 dark:text-gray-400 mt-1">
              Immutable enterprise ledger of systemic actions and modifications.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button className="px-4 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors shadow-sm flex items-center gap-2">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/></svg>
              Export CSV
            </button>
          </div>
        </header>

        {/* Filters */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <input 
            type="date" 
            className="w-full px-4 py-2.5 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-sm text-gray-700 dark:text-gray-300" 
          />
          <select className="px-4 py-2.5 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg text-sm text-gray-700 dark:text-gray-300 focus:ring-2 focus:ring-blue-500 outline-none">
            <option>Category: All</option>
            <option>AUTH</option>
            <option>RBAC</option>
            <option>USER_MANAGEMENT</option>
            <option>INVENTORY</option>
          </select>
          <div className="relative md:col-span-2">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <svg className="h-5 w-5 text-gray-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
            </div>
            <input type="text" className="w-full pl-10 pr-4 py-2.5 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition-all text-sm" placeholder="Search by actor, IP, or resource ID..." />
          </div>
        </div>

        {/* Data Table */}
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl shadow-sm overflow-hidden flex flex-col md:flex-row min-h-[500px]">
          
          {/* Logs List */}
          <div className={`w-full ${selectedLog ? 'md:w-1/2 border-r border-gray-200 dark:border-gray-800' : ''} transition-all duration-300`}>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-800">
                    <th className="px-6 py-4 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Timestamp</th>
                    <th className="px-6 py-4 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Actor & IP</th>
                    <th className="px-6 py-4 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                  {dummyLogs.map((log) => (
                    <tr 
                      key={log.id} 
                      onClick={() => setSelectedLog(log)}
                      className={`cursor-pointer transition-colors ${selectedLog?.id === log.id ? 'bg-blue-50 dark:bg-blue-900/10' : 'hover:bg-gray-50 dark:hover:bg-gray-800/50'}`}
                    >
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {log.timestamp}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900 dark:text-gray-200">{log.actor}</div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">{log.ip}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <span className="inline-flex px-2 py-0.5 rounded text-[10px] font-bold bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400 border border-gray-200 dark:border-gray-700">
                            {log.category}
                          </span>
                          <span className="text-sm font-medium text-gray-900 dark:text-gray-300">{log.action}</span>
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400 mt-1 truncate max-w-[200px]">
                          {log.resource}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Details Inspector Pane */}
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
                    <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Status</div>
                    <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">
                      {selectedLog.status}
                    </span>
                  </div>
                </div>

                <div className="border-t border-gray-200 dark:border-gray-800 pt-4">
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-3 uppercase tracking-wider font-semibold">Delta Tracking</div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-red-50 dark:bg-red-900/10 border border-red-100 dark:border-red-900/30 rounded-lg p-3">
                      <div className="text-xs font-semibold text-red-600 dark:text-red-400 mb-2">Old Value</div>
                      <pre className="text-[10px] sm:text-xs text-red-800 dark:text-red-300 font-mono overflow-x-auto">
{`{
  "role_id": null
}`}
                      </pre>
                    </div>
                    <div className="bg-emerald-50 dark:bg-emerald-900/10 border border-emerald-100 dark:border-emerald-900/30 rounded-lg p-3">
                      <div className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 mb-2">New Value</div>
                      <pre className="text-[10px] sm:text-xs text-emerald-800 dark:text-emerald-300 font-mono overflow-x-auto">
{`{
  "role_id": "c1f7b...9a2",
  "assigned_by": "Jane Smith"
}`}
                      </pre>
                    </div>
                  </div>
                </div>

                <div className="border-t border-gray-200 dark:border-gray-800 pt-4">
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-3 uppercase tracking-wider font-semibold">Network Trace</div>
                  <pre className="text-xs text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 p-3 rounded-lg overflow-x-auto font-mono">
{`User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...
IP: ${selectedLog.ip}
Correlation-ID: req_8f2b3a1`}
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
