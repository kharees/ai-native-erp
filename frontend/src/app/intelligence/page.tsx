'use client';
import React, { useState } from 'react';

export default function IntelligenceDashboardPage() {
  const [nlQuery, setNlQuery] = useState('');
  const [nlResult, setNlResult] = useState<string | null>(null);

  const securityScore = 85;

  const incidents = [
    { id: 1, type: 'IMPOSSIBLE_TRAVEL', time: '10 mins ago', desc: 'Login from US and CN within 2 hours (user: admin@example.com)', severity: 'high' },
    { id: 2, type: 'BRUTE_FORCE', time: '1 hour ago', desc: '45 failed login attempts detected on user_123', severity: 'high' },
    { id: 3, type: 'PRIVILEGE_ESCALATION', time: '3 hours ago', desc: 'User granted Super Admin without standard request flow', severity: 'medium' }
  ];

  const recommendations = [
    { id: 1, user: 'jane.doe@example.com', role: 'Finance Manager', reason: 'High department match with missing permissions.', confidence: 92 },
    { id: 2, user: 'john.smith@example.com', role: 'Warehouse Staff', reason: 'Assigned to Warehouse A but lacks physical inventory read access.', confidence: 88 }
  ];

  const handleAuditSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!nlQuery) return;
    setNlResult(`[AI ANALYSIS]: Based on the audit logs for "${nlQuery}", I found 3 relevant actions. Jane Smith modified the Finance Manager role at 14:30 UTC yesterday.`);
  };

  return (
    <div className="min-h-screen bg-gray-50/50 dark:bg-[#0a0a0a] p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Header Section */}
        <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white flex items-center gap-3">
              Intelligence Command Center
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gradient-to-r from-purple-500 to-indigo-600 text-white shadow-sm">
                AI ACTIVE
              </span>
            </h1>
            <p className="text-gray-500 dark:text-gray-400 mt-1">
              Real-time heuristic and generative AI monitoring of your identity and security perimeter.
            </p>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Left Column: Security Score & Incidents */}
          <div className="lg:col-span-1 space-y-8">
            
            {/* Security Score Card */}
            <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-6 shadow-sm relative overflow-hidden">
              <div className="absolute top-0 right-0 p-32 bg-gradient-to-br from-indigo-500/10 to-purple-500/5 rounded-full blur-3xl -mr-16 -mt-16 pointer-events-none"></div>
              <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">Organization Security Score</h3>
              <div className="flex items-end gap-4">
                <span className={`text-6xl font-black tracking-tighter ${securityScore > 80 ? 'text-emerald-500' : 'text-amber-500'}`}>
                  {securityScore}
                </span>
                <span className="text-sm font-medium text-gray-400 dark:text-gray-500 mb-2">/ 100</span>
              </div>
              <div className="mt-4 flex items-center gap-2 text-sm font-medium text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-500/10 px-3 py-2 rounded-lg w-fit">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6"/></svg>
                Trend: Decreasing (Action Required)
              </div>
            </div>

            {/* Threat Timeline */}
            <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">Threat Timeline</h3>
              <div className="space-y-6 relative before:absolute before:inset-0 before:ml-2.5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-gray-200 dark:before:via-gray-800 before:to-transparent">
                {incidents.map((incident) => (
                  <div key={incident.id} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                    <div className={`flex items-center justify-center w-5 h-5 rounded-full border-2 border-white dark:border-gray-900 shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 shadow-sm ${incident.severity === 'high' ? 'bg-red-500' : 'bg-amber-500'}`}></div>
                    <div className="w-[calc(100%-2.5rem)] md:w-[calc(50%-1.5rem)] p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/50 shadow-sm">
                      <div className="flex items-center justify-between mb-1">
                        <span className={`text-xs font-bold ${incident.severity === 'high' ? 'text-red-600 dark:text-red-400' : 'text-amber-600 dark:text-amber-400'}`}>{incident.type}</span>
                        <span className="text-[10px] text-gray-400">{incident.time}</span>
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-300">{incident.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            
          </div>

          {/* Right Column: Recommendations & Copilot */}
          <div className="lg:col-span-2 space-y-8">
            
            {/* Identity Radar: Recommendations */}
            <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl shadow-sm overflow-hidden">
              <div className="p-6 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between bg-gradient-to-r from-gray-50 to-white dark:from-gray-900 dark:to-gray-800/50">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <svg className="w-5 h-5 text-purple-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
                  Smart Role Recommendations
                </h3>
                <span className="text-xs font-medium text-gray-500 dark:text-gray-400">Generated by IdentityAnalyzer AI</span>
              </div>
              <div className="divide-y divide-gray-200 dark:divide-gray-800">
                {recommendations.map((rec) => (
                  <div key={rec.id} className="p-6 hover:bg-gray-50 dark:hover:bg-gray-800/20 transition-colors">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-sm font-semibold text-gray-900 dark:text-white">{rec.user}</span>
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-purple-50 text-purple-700 dark:bg-purple-500/10 dark:text-purple-400 border border-purple-200 dark:border-purple-900/50">
                            {rec.confidence}% Match
                          </span>
                        </div>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          <strong className="text-gray-900 dark:text-gray-200 font-medium">Suggestion: </strong> 
                          Assign <span className="bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400 px-1.5 py-0.5 rounded text-xs border border-blue-200 dark:border-blue-800">{rec.role}</span>
                        </p>
                        <p className="text-xs text-gray-500 mt-2 italic flex items-start gap-1.5">
                          <span className="text-purple-500 shrink-0">✦</span>
                          {rec.reason}
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <button className="px-3 py-1.5 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 rounded-lg text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">Dismiss</button>
                        <button className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors shadow-sm">Apply Role</button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Copilot Chat */}
            <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl shadow-sm overflow-hidden flex flex-col h-[400px]">
              <div className="p-4 border-b border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900 flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-inner">
                  <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/></svg>
                </div>
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
                      <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{nlResult}</p>
                      <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700 flex gap-2">
                         <span className="text-[10px] font-mono bg-gray-100 dark:bg-gray-900 text-gray-500 px-2 py-1 rounded">Confidence: 95%</span>
                         <span className="text-[10px] font-mono bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 border border-blue-100 dark:border-blue-800 px-2 py-1 rounded cursor-pointer hover:bg-blue-100 dark:hover:bg-blue-900/40">View Source Logs (2)</span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-center space-y-4">
                    <svg className="w-12 h-12 text-gray-300 dark:text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1"><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
                    <div className="space-y-1">
                      <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Ask the audit ledger anything.</p>
                      <p className="text-xs text-gray-400 dark:text-gray-600">"Who changed the finance settings last week?"</p>
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
                  <button type="submit" className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors">
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
