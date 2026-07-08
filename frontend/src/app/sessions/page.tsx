'use client';
import React, { useState } from 'react';

export default function SessionManagementPage() {
  const [activeTab, setActiveTab] = useState('sessions');

  const activeSessions = [
    {
      id: "sess_09a8f7b",
      device: "MacBook Pro 16\"",
      os: "macOS Sonoma",
      browser: "Chrome 122",
      ip: "192.168.1.105",
      location: "San Francisco, CA",
      lastActive: "Just now",
      isCurrent: true
    },
    {
      id: "sess_11b2c3d",
      device: "iPhone 15 Pro",
      os: "iOS 17",
      browser: "Safari Mobile",
      ip: "172.56.21.4",
      location: "San Jose, CA",
      lastActive: "2 hours ago",
      isCurrent: false
    }
  ];

  const trustedDevices = [
    {
      id: "dev_99x8",
      name: "Jane's Work MacBook",
      fingerprint: "a8f7b6c5d4e3...",
      os: "macOS Sonoma",
      lastSeen: "Today at 9:00 AM",
      status: "Trusted"
    }
  ];

  return (
    <div className="min-h-screen bg-gray-50/50 dark:bg-[#0a0a0a] p-8">
      <div className="max-w-6xl mx-auto space-y-8">
        
        {/* Header Section */}
        <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white">Active Sessions</h1>
            <p className="text-gray-500 dark:text-gray-400 mt-1">
              Manage your signed-in devices and active web sessions.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button className="px-4 py-2 bg-red-50 text-red-600 dark:bg-red-500/10 dark:text-red-400 border border-red-200 dark:border-red-900/50 hover:bg-red-100 dark:hover:bg-red-500/20 rounded-lg text-sm font-medium transition-colors shadow-sm flex items-center gap-2">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/></svg>
              Sign out all other sessions
            </button>
          </div>
        </header>

        {/* Navigation Tabs */}
        <div className="border-b border-gray-200 dark:border-gray-800">
          <nav className="-mb-px flex space-x-8">
            {['sessions', 'devices'].map((tab) => (
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

        {/* Tab Content: Active Sessions */}
        {activeTab === 'sessions' && (
          <div className="space-y-4">
            {activeSessions.map((session) => (
              <div key={session.id} className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="flex items-start gap-4">
                  <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    {session.os.includes('mac') || session.os.includes('iOS') ? (
                       <svg className="w-8 h-8 text-gray-600 dark:text-gray-300" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.477 2 2 6.477 2 12s4.477 10 10 10 10-4.477 10-10S17.523 2 12 2zm3.176 13.916c-.732-.014-1.424-.265-2.02-.733-.596-.468-1.026-1.106-1.258-1.865a3.914 3.914 0 0 1 .15-2.285c.29-.757.804-1.405 1.488-1.87.03-.022.062-.042.094-.06-.118-.17-.26-.324-.422-.46-.665-.558-1.503-.86-2.378-.86-.874 0-1.713.302-2.378.86-.546.458-.962 1.054-1.216 1.738-.255.684-.334 1.427-.23 2.164.103.737.382 1.436.81 2.038.43.602 1.002 1.08 1.666 1.393.665.312 1.395.46 2.13.432.735-.028 1.452-.233 2.093-.597a4.015 4.015 0 0 0 .97-.736zM13.684 6.74c-.58.113-1.185.04-1.73-.21-.546-.25-1.01-.645-1.332-1.135-.32-.49-.485-1.06-.475-1.637.01-.577.197-1.137.537-1.605.58-.113 1.185-.04 1.73.21.545.25 1.01.646 1.33 1.136.32.49.486 1.06.476 1.637-.01.577-.197 1.137-.536 1.604z"/></svg>
                    ) : (
                       <svg className="w-8 h-8 text-gray-600 dark:text-gray-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" x2="16" y1="21" y2="21"/><line x1="12" x2="12" y1="17" y2="21"/></svg>
                    )}
                  </div>
                  <div>
                    <h3 className="text-base font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                      {session.device} 
                      {session.isCurrent && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400">
                          THIS DEVICE
                        </span>
                      )}
                    </h3>
                    <div className="text-sm text-gray-500 dark:text-gray-400 mt-1 flex flex-wrap gap-x-4 gap-y-1">
                      <span>{session.browser} on {session.os}</span>
                      <span className="flex items-center gap-1">
                        <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
                        {session.location}
                      </span>
                      <span>IP: {session.ip}</span>
                    </div>
                    <div className="text-xs text-gray-400 dark:text-gray-500 mt-2">
                      Last active: {session.lastActive}
                    </div>
                  </div>
                </div>
                {!session.isCurrent && (
                  <button className="self-start md:self-center px-4 py-2 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-lg text-sm font-medium transition-colors text-gray-700 dark:text-gray-300">
                    Revoke Session
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Tab Content: Devices */}
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
                   {trustedDevices.map(device => (
                     <tr key={device.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/20 transition-colors">
                       <td className="px-6 py-4 whitespace-nowrap">
                         <div className="text-sm font-medium text-gray-900 dark:text-gray-200">{device.name}</div>
                         <div className="text-xs text-gray-500 dark:text-gray-400">{device.os}</div>
                       </td>
                       <td className="px-6 py-4 whitespace-nowrap">
                         <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-900/50">
                           <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                           {device.status}
                         </span>
                       </td>
                       <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                         {device.lastSeen}
                       </td>
                       <td className="px-6 py-4 whitespace-nowrap">
                         <button className="text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 text-sm font-medium">
                           Revoke Trust
                         </button>
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
