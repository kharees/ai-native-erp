'use client';

import React, { useState, useEffect } from 'react';
import { Database, Plus, RefreshCw, CheckCircle, XCircle, Clock, Server, Play, ShieldAlert, Activity } from 'lucide-react';

// Mock types since we don't have the exact API client generated here
interface ERPConnector {
  id: string;
  name: string;
  erp_type: string;
  is_active: boolean;
  last_sync_at: string | null;
  health_status: string;
}

export default function ERPConnectorsPage() {
  const [connectors, setConnectors] = useState<ERPConnector[]>([
    {
      id: '1',
      name: 'Tally Server - HQ',
      erp_type: 'TALLY',
      is_active: true,
      last_sync_at: '2023-10-27T10:00:00Z',
      health_status: 'SUCCESS',
    },
    {
      id: '2',
      name: 'SAP S/4HANA Global',
      erp_type: 'SAP',
      is_active: true,
      last_sync_at: null,
      health_status: 'UNKNOWN',
    }
  ]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [isSyncing, setIsSyncing] = useState<string | null>(null);

  const handleTestConnection = (id: string) => {
    // Mock testing
    setConnectors(prev => prev.map(c => 
      c.id === id ? { ...c, health_status: 'TESTING' } : c
    ));
    setTimeout(() => {
      setConnectors(prev => prev.map(c => 
        c.id === id ? { ...c, health_status: 'SUCCESS' } : c
      ));
    }, 1500);
  };

  const handleSync = (id: string) => {
    setIsSyncing(id);
    setTimeout(() => {
      setIsSyncing(null);
      setConnectors(prev => prev.map(c => 
        c.id === id ? { ...c, last_sync_at: new Date().toISOString() } : c
      ));
    }, 3000);
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 p-8 font-sans text-slate-800 dark:text-slate-200">
      <div className="max-w-6xl mx-auto space-y-8">
        
        {/* Header */}
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 dark:text-white flex items-center gap-3">
              <Server className="w-8 h-8 text-indigo-500" />
              Enterprise ERP Connectors
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-2">
              Manage live connections to external ERPs (Tally, SAP, Oracle) for automated data synchronization.
            </p>
          </div>
          <button 
            onClick={() => setShowAddModal(true)}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-semibold flex items-center gap-2 transition-colors shadow-sm"
          >
            <Plus className="w-4 h-4" /> Add Connector
          </button>
        </header>

        {/* Dashboard Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 flex items-center gap-4">
            <div className="p-3 bg-blue-100 dark:bg-blue-900/30 text-blue-600 rounded-lg">
              <Server className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm text-slate-500 font-medium">Active Connectors</p>
              <h3 className="text-2xl font-bold text-slate-900 dark:text-white">2</h3>
            </div>
          </div>
          <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 flex items-center gap-4">
            <div className="p-3 bg-green-100 dark:bg-green-900/30 text-green-600 rounded-lg">
              <RefreshCw className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm text-slate-500 font-medium">Records Synced (Today)</p>
              <h3 className="text-2xl font-bold text-slate-900 dark:text-white">4,892</h3>
            </div>
          </div>
          <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 flex items-center gap-4">
            <div className="p-3 bg-red-100 dark:bg-red-900/30 text-red-600 rounded-lg">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm text-slate-500 font-medium">Failed Syncs</p>
              <h3 className="text-2xl font-bold text-slate-900 dark:text-white">0</h3>
            </div>
          </div>
        </div>

        {/* Connectors Grid */}
        <h2 className="text-xl font-bold text-slate-900 dark:text-white pt-4">Configured Connectors</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {connectors.map(connector => (
            <div key={connector.id} className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
              <div className="flex justify-between items-start mb-4">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${connector.erp_type === 'SAP' ? 'bg-blue-100 text-blue-600' : 'bg-orange-100 text-orange-600'}`}>
                    <Database className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="font-bold text-lg">{connector.name}</h3>
                    <p className="text-sm text-slate-500 font-medium">{connector.erp_type} Integration</p>
                  </div>
                </div>
                <div>
                  {connector.health_status === 'SUCCESS' ? (
                     <span className="px-3 py-1 bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 rounded-full text-xs font-semibold flex items-center gap-1">
                      <CheckCircle className="w-3 h-3" /> Healthy
                    </span>
                  ) : connector.health_status === 'TESTING' ? (
                     <span className="px-3 py-1 bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 rounded-full text-xs font-semibold flex items-center gap-1">
                      <RefreshCw className="w-3 h-3 animate-spin" /> Testing...
                    </span>
                  ) : (
                    <span className="px-3 py-1 bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300 rounded-full text-xs font-semibold flex items-center gap-1">
                      <Activity className="w-3 h-3" /> Unknown
                    </span>
                  )}
                </div>
              </div>

              <div className="bg-slate-50 dark:bg-slate-900 rounded-lg p-4 mb-6 border border-slate-100 dark:border-slate-800">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Last Synced</span>
                  <span className="font-medium flex items-center gap-1">
                    <Clock className="w-3 h-3" /> 
                    {connector.last_sync_at ? new Date(connector.last_sync_at).toLocaleString() : 'Never'}
                  </span>
                </div>
                <div className="flex justify-between text-sm mt-2">
                  <span className="text-slate-500">Auto Sync</span>
                  <span className="font-medium text-indigo-600 dark:text-indigo-400">Enabled (Every 1h)</span>
                </div>
              </div>

              <div className="flex gap-3">
                <button 
                  onClick={() => handleTestConnection(connector.id)}
                  disabled={connector.health_status === 'TESTING'}
                  className="flex-1 px-4 py-2 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-800 dark:text-slate-200 rounded-lg text-sm font-semibold transition-colors flex justify-center items-center gap-2"
                >
                  <Activity className="w-4 h-4" /> Test Connection
                </button>
                <button 
                  onClick={() => handleSync(connector.id)}
                  disabled={isSyncing === connector.id}
                  className="flex-1 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-semibold transition-colors shadow-sm flex justify-center items-center gap-2 disabled:opacity-70"
                >
                  {isSyncing === connector.id ? (
                    <><RefreshCw className="w-4 h-4 animate-spin" /> Syncing...</>
                  ) : (
                    <><Play className="w-4 h-4" /> Manual Sync</>
                  )}
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Add Connector Modal (Mock) */}
        {showAddModal && (
          <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center z-50 animate-in fade-in">
            <div className="bg-white dark:bg-slate-800 rounded-xl shadow-xl border border-slate-200 dark:border-slate-700 w-full max-w-lg p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-bold">Add New ERP Connector</h2>
                <button onClick={() => setShowAddModal(false)} className="text-slate-400 hover:text-slate-600"><XCircle className="w-6 h-6" /></button>
              </div>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Connector Name</label>
                  <input type="text" className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg p-2" placeholder="e.g. Oracle NetSuite" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">ERP Type</label>
                  <select className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg p-2">
                    <option>Tally Prime</option>
                    <option>SAP S/4HANA</option>
                    <option>Oracle NetSuite</option>
                    <option>Microsoft Dynamics 365</option>
                    <option>Odoo</option>
                    <option>Zoho</option>
                    <option>QuickBooks</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Endpoint URL</label>
                  <input type="text" className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg p-2" placeholder="https://api.erp.example.com" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                   <div>
                    <label className="block text-sm font-medium mb-1">Client ID</label>
                    <input type="text" className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg p-2" placeholder="***" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Client Secret</label>
                    <input type="password" className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg p-2" placeholder="***" />
                  </div>
                </div>
                <button 
                  onClick={() => setShowAddModal(false)}
                  className="w-full mt-4 px-4 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-bold transition-colors shadow-md"
                >
                  Save Connection
                </button>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
