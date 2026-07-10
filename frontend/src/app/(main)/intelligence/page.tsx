'use client';
import React, { useState, useEffect } from 'react';
import apiClient, { isApiError } from '@/lib/apiClient';

interface RoleRecommendation {
  user_id: string;
  email: string;
  recommended_role: string;
  reason: string;
  confidence: number;
}

interface SecurityScore {
  score: number;
  trend: string;
  active_incidents: string[];
}

export default function IntelligenceDashboardPage() {
  const [nlQuery, setNlQuery] = useState('');
  const [nlResult, setNlResult] = useState<{ ai_summary: string; confidence: number; relevant_log_ids: string[] } | null>(null);
  const [nlLoading, setNlLoading] = useState(false);
  const [security, setSecurity] = useState<SecurityScore | null>(null);
  const [recommendations, setRecommendations] = useState<RoleRecommendation[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      apiClient.get('/api/v1/intelligence/security/risk-scores'),
      apiClient.get('/api/v1/intelligence/identity/recommendations'),
    ])
      .then(([secRes, recRes]) => {
        setSecurity(secRes.data);
        setRecommendations(recRes.data || []);
      })
      .catch((err) => setError(isApiError(err) ? err.message : 'Failed to load intelligence dashboard'))
      .finally(() => setLoading(false));
  }, []);

  const handleAuditSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nlQuery.trim()) return;
    setNlLoading(true);
    setError('');
    try {
      const res = await apiClient.post('/api/v1/intelligence/audit/natural-language-search', { query: nlQuery });
      setNlResult(res.data);
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to query audit intelligence');
    } finally {
      setNlLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50/50 dark:bg-[#0a0a0a] p-8">
      <div className="max-w-7xl mx-auto space-y-8">

        <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white flex items-center gap-3">
              Intelligence Command Center
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gradient-to-r from-purple-500 to-indigo-600 text-white shadow-sm">
                AI ACTIVE
              </span>
            </h1>
            <p className="text-gray-500 dark:text-gray-400 mt-1">
              Real-time heuristic monitoring of your identity and security perimeter.
            </p>
          </div>
        </header>

        {error && (
          <div className="p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

          <div className="lg:col-span-1 space-y-8">

            <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-6 shadow-sm relative overflow-hidden">
              <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">Organization Security Score</h3>
              {loading ? (
                <p className="text-sm text-gray-500">Loading...</p>
              ) : security ? (
                <>
                  <div className="flex items-end gap-4">
                    <span className={`text-6xl font-black tracking-tighter ${security.score > 80 ? 'text-emerald-500' : 'text-amber-500'}`}>
                      {security.score}
                    </span>
                    <span className="text-sm font-medium text-gray-400 dark:text-gray-500 mb-2">/ 100</span>
                  </div>
                  <div className="mt-4 flex items-center gap-2 text-sm font-medium text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-500/10 px-3 py-2 rounded-lg w-fit">
                    Trend: {security.trend}
                  </div>
                </>
              ) : (
                <p className="text-sm text-gray-500">No data available.</p>
              )}
            </div>

            <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">Active Incidents</h3>
              {!security || security.active_incidents.length === 0 ? (
                <p className="text-sm text-gray-500">No active incidents detected.</p>
              ) : (
                <div className="space-y-3">
                  {security.active_incidents.map((incident, i) => (
                    <div key={i} className="p-4 rounded-xl border border-red-200 dark:border-red-900/50 bg-red-50/50 dark:bg-red-900/10">
                      <p className="text-sm text-red-700 dark:text-red-300">{incident}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>

          </div>

          <div className="lg:col-span-2 space-y-8">

            <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl shadow-sm overflow-hidden">
              <div className="p-6 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between bg-gradient-to-r from-gray-50 to-white dark:from-gray-900 dark:to-gray-800/50">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  Smart Role Recommendations
                </h3>
                <span className="text-xs font-medium text-gray-500 dark:text-gray-400">Generated by IdentityAnalyzer AI</span>
              </div>
              <div className="divide-y divide-gray-200 dark:divide-gray-800">
                {loading ? (
                  <div className="p-6 text-sm text-gray-500">Loading recommendations...</div>
                ) : recommendations.length === 0 ? (
                  <div className="p-6 text-sm text-gray-500">No role recommendations at this time.</div>
                ) : recommendations.map((rec) => (
                  <div key={rec.user_id} className="p-6 hover:bg-gray-50 dark:hover:bg-gray-800/20 transition-colors">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-semibold text-gray-900 dark:text-white">{rec.email}</span>
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-purple-50 text-purple-700 dark:bg-purple-500/10 dark:text-purple-400 border border-purple-200 dark:border-purple-900/50">
                          {Math.round(rec.confidence)}% Match
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        <strong className="text-gray-900 dark:text-gray-200 font-medium">Suggestion: </strong>
                        Assign <span className="bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400 px-1.5 py-0.5 rounded text-xs border border-blue-200 dark:border-blue-800">{rec.recommended_role}</span>
                      </p>
                      <p className="text-xs text-gray-500 mt-2 italic">{rec.reason}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl shadow-sm overflow-hidden flex flex-col h-[400px]">
              <div className="p-4 border-b border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900 flex items-center gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Audit Copilot</h3>
                  <p className="text-[10px] text-gray-500 dark:text-gray-400">Natural Language Audit Intelligence</p>
                </div>
              </div>

              <div className="flex-1 p-6 overflow-y-auto bg-gray-50/30 dark:bg-[#0c0c0c]">
                {nlResult ? (
                  <div className="flex gap-4">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 shrink-0 flex items-center justify-center">
                      <span className="text-white text-xs font-bold">AI</span>
                    </div>
                    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-4 rounded-2xl rounded-tl-none shadow-sm max-w-[85%]">
                      <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{nlResult.ai_summary}</p>
                      <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700 flex gap-2">
                        <span className="text-[10px] font-mono bg-gray-100 dark:bg-gray-900 text-gray-500 px-2 py-1 rounded">Confidence: {Math.round(nlResult.confidence)}%</span>
                        <span className="text-[10px] font-mono bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 border border-blue-100 dark:border-blue-800 px-2 py-1 rounded">
                          Source Logs: {nlResult.relevant_log_ids.length}
                        </span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-center space-y-4">
                    <div className="space-y-1">
                      <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Ask the audit ledger anything.</p>
                      <p className="text-xs text-gray-400 dark:text-gray-600">&quot;Who changed the finance settings last week?&quot;</p>
                    </div>
                  </div>
                )}
              </div>

              <div className="p-4 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800">
                <form onSubmit={handleAuditSearch} className="relative">
                  <input
                    type="text"
                    value={nlQuery}
                    onChange={(e) => setNlQuery(e.target.value)}
                    placeholder="Ask Copilot..."
                    className="w-full pl-4 pr-12 py-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm focus:ring-2 focus:ring-purple-500 outline-none text-gray-900 dark:text-white placeholder-gray-400"
                  />
                  <button type="submit" disabled={nlLoading || !nlQuery.trim()} className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors disabled:opacity-50">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
                  </button>
                </form>
              </div>
            </div>

          </div>
        </div>

      </div>
    </div>
  );
}
