'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import {
  Play, Pause, Square, RotateCcw, CheckCircle,
  Clock, Activity, ShieldAlert, BarChart3
} from 'lucide-react';
import apiClient, { isApiError } from '@/lib/apiClient';

interface Session {
  id: string;
  entity_type: string;
  original_file_name: string;
  status: string;
  total_records: number;
  imported_records: number;
}

interface ExecutionStatus {
  session_id: string;
  status: string;
  progress_percentage: number;
  imported_records: number;
  skipped_records: number;
  failed_records: number;
  processing_speed_mps: number;
  estimated_remaining_time_sec: number;
  message: string;
}

interface ReconciliationReport {
  missing_records: number;
  duplicate_records: number;
  mismatched_records: number;
  import_accuracy_percentage: number;
}

const HUB_BASE = '/api/v1/migration';
const EXEC_BASE = '/api/v1/migration/execution';

export default function MigrationExecutionPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [sessionId, setSessionId] = useState('');
  const [status, setStatus] = useState<ExecutionStatus | null>(null);
  const [reconciliation, setReconciliation] = useState<ReconciliationReport | null>(null);
  const [activeTab, setActiveTab] = useState<'dashboard' | 'reconciliation'>('dashboard');
  const [error, setError] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    apiClient
      .get(`${HUB_BASE}/sessions`)
      .then((res) => setSessions(res.data || []))
      .catch(() => setError('Failed to load migration sessions'));
  }, []);

  const loadStatus = useCallback(() => {
    if (!sessionId) return;
    apiClient
      .get(`${EXEC_BASE}/${sessionId}/status`)
      .then((res) => setStatus(res.data))
      .catch((err) => setError(isApiError(err) ? err.message : 'Failed to load execution status'));
  }, [sessionId]);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  const handleAction = async (action: 'execute' | 'pause' | 'resume' | 'cancel' | 'rollback') => {
    if (!sessionId) return;
    setActionLoading(true);
    setError('');
    try {
      if (action === 'rollback') {
        await apiClient.post(`${EXEC_BASE}/${sessionId}/rollback`, { partial: false });
      } else {
        await apiClient.post(`${EXEC_BASE}/${sessionId}/${action}`);
      }
      loadStatus();
    } catch (err) {
      setError(isApiError(err) ? err.message : `Failed to ${action} migration`);
    } finally {
      setActionLoading(false);
    }
  };

  const loadReconciliation = async () => {
    if (!sessionId) return;
    setActionLoading(true);
    setError('');
    try {
      const res = await apiClient.post(`${EXEC_BASE}/${sessionId}/reconcile`);
      setReconciliation(res.data);
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to generate reconciliation report');
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 p-8 font-sans text-slate-800 dark:text-slate-200">
      <div className="max-w-6xl mx-auto space-y-8">
        <Link href="/migration" className="text-indigo-600 hover:underline text-sm block">&larr; Back to Migration Hub</Link>

        <header className="bg-white dark:bg-slate-800 p-6 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 space-y-4">
          <h1 className="text-2xl font-bold flex items-center gap-3">
            <Activity className="w-7 h-7 text-indigo-500" />
            Migration Execution Engine
          </h1>
          <select
            value={sessionId}
            onChange={(e) => { setSessionId(e.target.value); setStatus(null); setReconciliation(null); }}
            className="w-full max-w-md p-2 border rounded dark:bg-slate-900 dark:border-slate-700 text-sm"
          >
            <option value="">- Select a migration session -</option>
            {sessions.map((s) => (
              <option key={s.id} value={s.id}>{s.original_file_name} ({s.entity_type}) - {s.status}</option>
            ))}
          </select>
        </header>

        {error && (
          <div className="p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
        )}

        {!sessionId ? (
          <p className="text-sm text-slate-500">Select a session above to view execution status.</p>
        ) : (
          <>
            <div className="flex items-center justify-between bg-white dark:bg-slate-800 p-4 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700">
              <span className={`px-3 py-1 rounded-full text-xs font-bold flex items-center gap-2 ${
                status?.status === 'IMPORTING' ? 'bg-indigo-100 text-indigo-700 animate-pulse' :
                status?.status === 'PAUSED' ? 'bg-amber-100 text-amber-700' :
                status?.status?.includes('ROLL') ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-700'
              }`}>
                <span className="w-2 h-2 rounded-full bg-current" />
                {status?.status || 'UNKNOWN'}
              </span>
              <div className="flex gap-3">
                <button onClick={() => handleAction('execute')} disabled={actionLoading} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-semibold flex items-center gap-2 disabled:opacity-50">
                  <Play className="w-4 h-4" /> Execute
                </button>
                <button onClick={() => handleAction('pause')} disabled={actionLoading} className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white rounded-lg font-semibold flex items-center gap-2 disabled:opacity-50">
                  <Pause className="w-4 h-4" /> Pause
                </button>
                <button onClick={() => handleAction('resume')} disabled={actionLoading} className="px-4 py-2 bg-slate-200 dark:bg-slate-700 rounded-lg font-semibold flex items-center gap-2 disabled:opacity-50">
                  <Play className="w-4 h-4" /> Resume
                </button>
                <button onClick={() => handleAction('cancel')} disabled={actionLoading} className="px-4 py-2 bg-slate-200 dark:bg-slate-700 rounded-lg font-semibold flex items-center gap-2 disabled:opacity-50">
                  <Square className="w-4 h-4" /> Cancel
                </button>
                <button onClick={() => handleAction('rollback')} disabled={actionLoading} className="px-4 py-2 bg-red-100 dark:bg-red-900/30 text-red-600 rounded-lg font-semibold flex items-center gap-2 disabled:opacity-50">
                  <RotateCcw className="w-4 h-4" /> Rollback
                </button>
              </div>
            </div>

            <div className="flex gap-4 border-b border-slate-200 dark:border-slate-800 pb-2">
              {[
                { id: 'dashboard', icon: BarChart3, label: 'Live Dashboard' },
                { id: 'reconciliation', icon: CheckCircle, label: 'Reconciliation' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as 'dashboard' | 'reconciliation')}
                  className={`flex items-center gap-2 px-4 py-2 font-semibold transition-all ${
                    activeTab === tab.id ? 'text-indigo-600 border-b-2 border-indigo-600' : 'text-slate-500'
                  }`}
                >
                  <tab.icon className="w-4 h-4" />
                  {tab.label}
                </button>
              ))}
            </div>

            {activeTab === 'dashboard' && (
              <div className="space-y-6">
                <div className="bg-white dark:bg-slate-800 p-6 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700">
                  <div className="flex justify-between items-end mb-4">
                    <h3 className="font-bold text-lg">Total Import Progress</h3>
                    <span className="text-3xl font-black text-indigo-600">{status?.progress_percentage ?? 0}%</span>
                  </div>
                  <div className="w-full bg-slate-100 dark:bg-slate-700 rounded-full h-4 mb-4 overflow-hidden border border-slate-200 dark:border-slate-600">
                    <div className="h-4 rounded-full bg-indigo-600 transition-all duration-1000" style={{ width: `${status?.progress_percentage ?? 0}%` }} />
                  </div>
                  <div className="flex justify-between text-sm font-medium text-slate-500">
                    <span>{status?.imported_records ?? 0} Records Imported</span>
                    <span className="flex items-center gap-1"><Clock className="w-4 h-4" /> Est. Remaining: {status?.estimated_remaining_time_sec ?? 0}s</span>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                  <div className="bg-white dark:bg-slate-800 p-5 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700">
                    <p className="text-sm font-semibold text-slate-500 mb-1">Speed</p>
                    <p className="text-2xl font-black">{status?.processing_speed_mps ?? 0} <span className="text-sm font-medium text-slate-400">rec/sec</span></p>
                  </div>
                  <div className="bg-white dark:bg-slate-800 p-5 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700">
                    <p className="text-sm font-semibold text-slate-500 mb-1">Imported</p>
                    <p className="text-2xl font-black text-green-600">{status?.imported_records ?? 0}</p>
                  </div>
                  <div className="bg-white dark:bg-slate-800 p-5 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700">
                    <p className="text-sm font-semibold text-slate-500 mb-1">Failed</p>
                    <p className="text-2xl font-black text-red-600">{status?.failed_records ?? 0}</p>
                  </div>
                  <div className="bg-white dark:bg-slate-800 p-5 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700">
                    <p className="text-sm font-semibold text-slate-500 mb-1">Skipped</p>
                    <p className="text-2xl font-black text-amber-500">{status?.skipped_records ?? 0}</p>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'reconciliation' && (
              <div className="space-y-6">
                <div className="flex items-center justify-between bg-white dark:bg-slate-800 p-6 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700">
                  <div>
                    <h2 className="text-xl font-bold flex items-center gap-2"><ShieldAlert className="w-6 h-6 text-indigo-500" /> Post-Import Reconciliation</h2>
                    <p className="text-sm text-slate-500 mt-1">Compares source file data against created ERP records.</p>
                  </div>
                  <button onClick={loadReconciliation} disabled={actionLoading} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-semibold disabled:opacity-50">
                    {actionLoading ? 'Generating...' : 'Generate Report'}
                  </button>
                </div>
                {reconciliation ? (
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                    <div className="bg-white dark:bg-slate-800 p-5 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700">
                      <p className="text-sm font-semibold text-slate-500 mb-1">Accuracy</p>
                      <p className="text-2xl font-black text-green-600">{reconciliation.import_accuracy_percentage}%</p>
                    </div>
                    <div className="bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-900/30 p-5 rounded-2xl">
                      <p className="text-sm font-bold text-red-800 dark:text-red-400">Missing</p>
                      <p className="text-2xl font-black text-red-600 mt-2">{reconciliation.missing_records}</p>
                    </div>
                    <div className="bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-900/30 p-5 rounded-2xl">
                      <p className="text-sm font-bold text-amber-800 dark:text-amber-400">Mismatched</p>
                      <p className="text-2xl font-black text-amber-600 mt-2">{reconciliation.mismatched_records}</p>
                    </div>
                    <div className="bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-900/30 p-5 rounded-2xl">
                      <p className="text-sm font-bold text-blue-800 dark:text-blue-400">Duplicates</p>
                      <p className="text-2xl font-black text-blue-600 mt-2">{reconciliation.duplicate_records}</p>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-slate-500">No reconciliation report generated yet.</p>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
