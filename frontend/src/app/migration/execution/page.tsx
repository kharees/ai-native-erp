'use client';

import React, { useState, useEffect } from 'react';
import { 
  Play, Pause, Square, RotateCcw, AlertTriangle, CheckCircle, 
  Clock, Activity, FileText, Download, ShieldAlert, BarChart3, Settings
} from 'lucide-react';

export default function MigrationExecutionPage() {
  const [status, setStatus] = useState<'IMPORTING' | 'PAUSED' | 'CANCELLING' | 'ROLLING_BACK' | 'ROLLED_BACK' | 'SUCCESS'>('PAUSED');
  const [progress, setProgress] = useState(45);
  const [activeTab, setActiveTab] = useState<'dashboard' | 'reconciliation' | 'rollback'>('dashboard');

  // Simulated metrics
  const totalRecords = 50000;
  const importedRecords = 22500;
  const failedRecords = 42;
  const speed = 1250; // mps
  const timeRemaining = 22; // seconds

  const handleAction = (action: string) => {
    switch (action) {
      case 'resume': setStatus('IMPORTING'); break;
      case 'pause': setStatus('PAUSED'); break;
      case 'cancel': setStatus('CANCELLING'); setTimeout(() => setStatus('ROLLED_BACK'), 2000); break;
      case 'rollback': setStatus('ROLLING_BACK'); setTimeout(() => setStatus('ROLLED_BACK'), 2000); break;
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 p-8 font-sans text-slate-800 dark:text-slate-200">
      <div className="max-w-6xl mx-auto space-y-8">
        
        {/* Header & Controls */}
        <header className="flex items-center justify-between bg-white dark:bg-slate-800 p-6 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-3">
              <Activity className="w-7 h-7 text-indigo-500" />
              Migration Execution Engine
            </h1>
            <div className="flex items-center gap-3 mt-2">
              <span className={`px-3 py-1 rounded-full text-xs font-bold flex items-center gap-2 
                ${status === 'IMPORTING' ? 'bg-indigo-100 text-indigo-700 animate-pulse' : 
                  status === 'PAUSED' ? 'bg-amber-100 text-amber-700' : 
                  status.includes('ROLL') ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-700'}`}>
                <span className="w-2 h-2 rounded-full bg-current" />
                {status.replace('_', ' ')}
              </span>
              <span className="text-sm font-medium text-slate-500">Session ID: <span className="font-mono text-xs">MIG-9982-FX</span></span>
            </div>
          </div>
          
          <div className="flex gap-3">
            {status === 'PAUSED' || status === 'ROLLED_BACK' ? (
              <button onClick={() => handleAction('resume')} className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold flex items-center gap-2 shadow-md transition-all">
                <Play className="w-4 h-4 fill-current" /> Resume
              </button>
            ) : status === 'IMPORTING' ? (
              <button onClick={() => handleAction('pause')} className="px-5 py-2.5 bg-amber-500 hover:bg-amber-600 text-white rounded-xl font-bold flex items-center gap-2 shadow-md transition-all">
                <Pause className="w-4 h-4 fill-current" /> Pause
              </button>
            ) : null}
            
            <button onClick={() => handleAction('cancel')} disabled={status === 'CANCELLING' || status === 'ROLLED_BACK'} className="px-5 py-2.5 bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600 rounded-xl font-bold flex items-center gap-2 transition-all disabled:opacity-50">
              <Square className="w-4 h-4 fill-current" /> Cancel
            </button>
            
            <button onClick={() => handleAction('rollback')} disabled={status === 'ROLLING_BACK' || status === 'ROLLED_BACK'} className="px-5 py-2.5 bg-red-100 dark:bg-red-900/30 text-red-600 hover:bg-red-200 dark:hover:bg-red-900/50 rounded-xl font-bold flex items-center gap-2 transition-all disabled:opacity-50">
              <RotateCcw className="w-4 h-4" /> Rollback
            </button>
          </div>
        </header>

        {/* Navigation Tabs */}
        <div className="flex gap-4 border-b border-slate-200 dark:border-slate-800 pb-2">
          {[
            { id: 'dashboard', icon: BarChart3, label: 'Live Dashboard' },
            { id: 'reconciliation', icon: CheckCircle, label: 'Reconciliation' },
            { id: 'rollback', icon: RotateCcw, label: 'Rollback History' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-2 font-semibold transition-all ${
                activeTab === tab.id
                  ? 'text-indigo-600 border-b-2 border-indigo-600'
                  : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* LIVE DASHBOARD TAB */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6 animate-in fade-in">
            {/* Progress Bar Component */}
            <div className="bg-white dark:bg-slate-800 p-6 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700">
              <div className="flex justify-between items-end mb-4">
                <div>
                  <h3 className="font-bold text-lg mb-1">Total Import Progress</h3>
                  <p className="text-sm text-slate-500">Processing records in batches of 5,000</p>
                </div>
                <div className="text-right">
                  <span className="text-3xl font-black text-indigo-600">{progress}%</span>
                </div>
              </div>
              <div className="w-full bg-slate-100 dark:bg-slate-700 rounded-full h-4 mb-4 overflow-hidden border border-slate-200 dark:border-slate-600">
                <div 
                  className={`h-4 rounded-full transition-all duration-1000 ${status === 'IMPORTING' ? 'bg-indigo-600' : status === 'PAUSED' ? 'bg-amber-500' : 'bg-red-500'}`} 
                  style={{ width: `${progress}%` }}
                >
                  {status === 'IMPORTING' && <div className="w-full h-full bg-white/20 animate-[shimmer_2s_infinite]" style={{ backgroundImage: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.5), transparent)' }}></div>}
                </div>
              </div>
              <div className="flex justify-between text-sm font-medium text-slate-500">
                <span>{importedRecords.toLocaleString()} / {totalRecords.toLocaleString()} Records</span>
                <span className="flex items-center gap-1"><Clock className="w-4 h-4" /> Est. Time Remaining: {timeRemaining}s</span>
              </div>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="bg-white dark:bg-slate-800 p-5 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700">
                <p className="text-sm font-semibold text-slate-500 mb-1">Speed</p>
                <p className="text-2xl font-black flex items-baseline gap-1">
                  {speed.toLocaleString()} <span className="text-sm font-medium text-slate-400">rec/sec</span>
                </p>
              </div>
              <div className="bg-white dark:bg-slate-800 p-5 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700">
                <p className="text-sm font-semibold text-slate-500 mb-1">Success</p>
                <p className="text-2xl font-black text-green-600">{importedRecords.toLocaleString()}</p>
              </div>
              <div className="bg-white dark:bg-slate-800 p-5 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700">
                <p className="text-sm font-semibold text-slate-500 mb-1">Failed</p>
                <p className="text-2xl font-black text-red-600">{failedRecords.toLocaleString()}</p>
              </div>
              <div className="bg-white dark:bg-slate-800 p-5 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700">
                <p className="text-sm font-semibold text-slate-500 mb-1">Skipped</p>
                <p className="text-2xl font-black text-amber-500">12</p>
              </div>
            </div>

            {/* Live Logs */}
            <div className="bg-slate-900 rounded-2xl shadow-sm border border-slate-800 p-6 overflow-hidden">
              <div className="flex justify-between items-center mb-4">
                <h3 className="font-bold text-white flex items-center gap-2"><FileText className="w-4 h-4" /> Live Execution Logs</h3>
                <button className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold flex items-center gap-1"><Download className="w-3 h-3" /> Export Logs</button>
              </div>
              <div className="space-y-2 font-mono text-xs overflow-y-auto max-h-48 scrollbar-thin">
                <p className="text-green-400">[2023-10-27 10:14:02] Batch 4 (15000-20000) committed successfully.</p>
                <p className="text-slate-400">[2023-10-27 10:14:05] Processing Batch 5 (20000-25000)...</p>
                <p className="text-amber-400">[2023-10-27 10:14:07] Row 22104: Skipping due to invalid target format.</p>
                <p className="text-red-400">[2023-10-27 10:14:08] Row 22500: Database lock timeout, retrying...</p>
                <p className="text-green-400">[2023-10-27 10:14:09] Row 22500: Retry successful.</p>
              </div>
            </div>
          </div>
        )}

        {/* RECONCILIATION TAB */}
        {activeTab === 'reconciliation' && (
          <div className="space-y-6 animate-in fade-in">
             <div className="flex items-center justify-between bg-white dark:bg-slate-800 p-6 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700">
                <div>
                  <h2 className="text-xl font-bold flex items-center gap-2"><ShieldAlert className="w-6 h-6 text-indigo-500"/> Post-Import Reconciliation</h2>
                  <p className="text-sm text-slate-500 mt-1">Comparing source file data against created ERP records.</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold text-slate-500">Data Accuracy</p>
                  <p className="text-3xl font-black text-green-500">99.8%</p>
                </div>
             </div>
             
             <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-900/30 p-5 rounded-2xl">
                  <p className="text-sm font-bold text-red-800 dark:text-red-400">Missing Records</p>
                  <p className="text-2xl font-black text-red-600 mt-2">0</p>
                  <p className="text-xs text-red-500 mt-1">Source records not found in DB</p>
                </div>
                <div className="bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-900/30 p-5 rounded-2xl">
                  <p className="text-sm font-bold text-amber-800 dark:text-amber-400">Value Mismatches</p>
                  <p className="text-2xl font-black text-amber-600 mt-2">12</p>
                  <p className="text-xs text-amber-500 mt-1">Fields altered during import</p>
                </div>
                <div className="bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-900/30 p-5 rounded-2xl">
                  <p className="text-sm font-bold text-blue-800 dark:text-blue-400">Duplicates Created</p>
                  <p className="text-2xl font-black text-blue-600 mt-2">3</p>
                  <p className="text-xs text-blue-500 mt-1">Identical records in DB</p>
                </div>
             </div>
             
             <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
                <h3 className="font-bold mb-4">Mismatch Details</h3>
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 dark:border-slate-700">
                      <th className="pb-3 font-semibold text-slate-500">Row ID</th>
                      <th className="pb-3 font-semibold text-slate-500">Field</th>
                      <th className="pb-3 font-semibold text-slate-500">Source Value</th>
                      <th className="pb-3 font-semibold text-slate-500">ERP Value</th>
                      <th className="pb-3 font-semibold text-slate-500">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr className="border-b border-slate-100 dark:border-slate-800/50">
                      <td className="py-3 font-mono">#4021</td>
                      <td className="py-3 font-medium">Balance</td>
                      <td className="py-3 text-amber-600 line-through">1,000.50</td>
                      <td className="py-3 text-green-600">1000.50</td>
                      <td className="py-3"><button className="text-indigo-600 font-semibold hover:underline">Accept ERP</button></td>
                    </tr>
                  </tbody>
                </table>
             </div>
          </div>
        )}

        {/* ROLLBACK TAB */}
        {activeTab === 'rollback' && (
          <div className="space-y-6 animate-in fade-in">
            <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
              <h2 className="text-xl font-bold flex items-center gap-2 mb-6"><RotateCcw className="w-6 h-6 text-slate-500"/> Rollback History</h2>
              
              <div className="space-y-4">
                <div className="p-4 border border-slate-200 dark:border-slate-700 rounded-xl flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-3 mb-1">
                      <span className="px-2.5 py-0.5 bg-green-100 text-green-700 text-xs font-bold rounded">SUCCESS</span>
                      <span className="font-bold text-slate-700 dark:text-slate-200">Partial Rollback (Batch 2)</span>
                    </div>
                    <p className="text-sm text-slate-500">Rolled back 5,000 records due to mapping error.</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium">Oct 27, 2023 - 09:14 AM</p>
                    <p className="text-xs text-slate-500">Initiated by Admin</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
