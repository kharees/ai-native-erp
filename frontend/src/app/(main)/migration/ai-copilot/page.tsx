'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Sparkles, Activity, ShieldAlert, HeartPulse, Wand2, MessageSquare, Send
} from 'lucide-react';
import apiClient, { isApiError } from '@/lib/apiClient';

interface Session {
  id: string;
  entity_type: string;
  original_file_name: string;
  status: string;
}

interface DataQualityMetric {
  category: string;
  issue_count: number;
  impact_level: string;
  description: string;
}

interface DataQualityReport {
  health_score: number;
  risk_score: number;
  metrics: DataQualityMetric[];
  overall_recommendation: string;
}

interface CleansingSuggestion {
  suggestion_id: string;
  type: string;
  description: string;
  affected_records_count: number;
  confidence_score: number;
}

const HUB_BASE = '/api/v1/migration';
const AI_BASE = '/api/v1/migration/ai-copilot';

export default function MigrationAICopilotPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [sessionId, setSessionId] = useState('');
  const [report, setReport] = useState<DataQualityReport | null>(null);
  const [suggestions, setSuggestions] = useState<CleansingSuggestion[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const [chatMessages, setChatMessages] = useState<{ role: 'user' | 'ai'; content: string }[]>([
    { role: 'ai', content: "Hi! I'm your Migration AI Copilot. Select a session, then ask me about errors, duplicates, or a summary." },
  ]);
  const [chatInput, setChatInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);

  useEffect(() => {
    apiClient
      .get(`${HUB_BASE}/sessions`)
      .then((res) => setSessions(res.data || []))
      .catch(() => setError('Failed to load migration sessions'));
  }, []);

  useEffect(() => {
    if (!sessionId) {
      setReport(null);
      setSuggestions([]);
      return;
    }
    setLoading(true);
    setError('');
    Promise.all([
      apiClient.get(`${AI_BASE}/${sessionId}/data-quality`),
      apiClient.get(`${AI_BASE}/${sessionId}/cleansing-suggestions`),
    ])
      .then(([qualityRes, suggestRes]) => {
        setReport(qualityRes.data);
        setSuggestions(suggestRes.data.suggestions || []);
      })
      .catch((err) => setError(isApiError(err) ? err.message : 'Failed to load AI diagnostics'))
      .finally(() => setLoading(false));
  }, [sessionId]);

  const handleSendMessage = async () => {
    if (!chatInput.trim() || !sessionId) return;
    const query = chatInput;
    setChatMessages((prev) => [...prev, { role: 'user', content: query }]);
    setChatInput('');
    setIsTyping(true);
    try {
      const res = await apiClient.post(`${AI_BASE}/${sessionId}/chat`, { query });
      setChatMessages((prev) => [...prev, { role: 'ai', content: res.data.response }]);
    } catch (err) {
      setChatMessages((prev) => [...prev, { role: 'ai', content: isApiError(err) ? err.message : 'Failed to get a response.' }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 p-8 font-sans text-slate-800 dark:text-slate-200">
      <div className="max-w-7xl mx-auto space-y-8">
        <Link href="/migration" className="text-indigo-600 hover:underline text-sm block">&larr; Back to Migration Hub</Link>

        <header className="flex items-center justify-between bg-white dark:bg-slate-800 p-6 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-3">
              <Sparkles className="w-7 h-7 text-indigo-500" />
              AI Migration Copilot
            </h1>
            <p className="text-sm text-slate-500 mt-1">Advisory intelligence for data quality and error analysis.</p>
          </div>
          <select
            value={sessionId}
            onChange={(e) => setSessionId(e.target.value)}
            className="p-2 border rounded dark:bg-slate-900 dark:border-slate-700 text-sm max-w-xs"
          >
            <option value="">- Select a migration session -</option>
            {sessions.map((s) => (
              <option key={s.id} value={s.id}>{s.original_file_name} ({s.entity_type})</option>
            ))}
          </select>
        </header>

        {error && (
          <div className="p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
        )}

        {!sessionId ? (
          <p className="text-sm text-slate-500">Select a migration session above to view AI diagnostics.</p>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2 space-y-8">
              {loading ? (
                <p className="text-sm text-slate-500">Loading AI diagnostics...</p>
              ) : report && (
                <>
                  <div className="grid grid-cols-2 gap-6">
                    <div className="bg-white dark:bg-slate-800 p-6 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700">
                      <div className="p-3 bg-green-100 dark:bg-green-900/30 text-green-600 rounded-xl w-fit mb-2">
                        <HeartPulse className="w-6 h-6" />
                      </div>
                      <p className="text-sm font-bold text-slate-500 mt-4">Migration Health Score</p>
                      <p className="text-4xl font-black text-slate-900 dark:text-white mt-1">{report.health_score}/100</p>
                    </div>
                    <div className="bg-white dark:bg-slate-800 p-6 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700">
                      <div className="p-3 bg-amber-100 dark:bg-amber-900/30 text-amber-600 rounded-xl w-fit mb-2">
                        <Activity className="w-6 h-6" />
                      </div>
                      <p className="text-sm font-bold text-slate-500 mt-4">Import Risk Score</p>
                      <p className="text-4xl font-black text-slate-900 dark:text-white mt-1">{report.risk_score}/100</p>
                    </div>
                  </div>

                  <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
                    <h2 className="text-lg font-bold flex items-center gap-2 mb-6"><ShieldAlert className="text-indigo-500" /> AI Data Quality Diagnostics</h2>
                    {report.metrics.length === 0 ? (
                      <p className="text-sm text-slate-500">No data quality issues detected.</p>
                    ) : (
                      <div className="space-y-4">
                        {report.metrics.map((metric, i) => (
                          <div key={i} className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-900 rounded-xl border border-slate-100 dark:border-slate-800">
                            <div>
                              <h4 className="font-bold">{metric.category}</h4>
                              <p className="text-sm text-slate-500">{metric.description}</p>
                            </div>
                            <div className="text-right">
                              <span className="text-xl font-bold">{metric.issue_count.toLocaleString()}</span>
                              <p className="text-xs text-slate-500">{metric.impact_level}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    <p className="text-sm text-slate-600 dark:text-slate-300 mt-4">{report.overall_recommendation}</p>
                  </div>

                  <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
                    <h2 className="text-lg font-bold flex items-center gap-2 mb-6"><Wand2 className="text-indigo-500" /> AI Cleansing Recommendations</h2>
                    {suggestions.length === 0 ? (
                      <p className="text-sm text-slate-500">No cleansing suggestions available.</p>
                    ) : (
                      <div className="space-y-4">
                        {suggestions.map((sug) => (
                          <div key={sug.suggestion_id} className="p-5 border border-indigo-100 dark:border-indigo-900/50 bg-indigo-50/50 dark:bg-indigo-900/10 rounded-xl">
                            <h4 className="font-bold text-indigo-900 dark:text-indigo-300">{sug.description}</h4>
                            <p className="text-sm text-slate-500 mt-1">Affects <span className="font-semibold text-slate-700 dark:text-slate-300">{sug.affected_records_count.toLocaleString()}</span> records.</p>
                            <div className="mt-3 flex items-center gap-2 text-xs font-bold text-indigo-600 dark:text-indigo-400">
                              <Sparkles className="w-3 h-3" /> {sug.confidence_score}% AI Confidence
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>

            <div className="lg:col-span-1">
              <div className="bg-slate-900 rounded-2xl shadow-lg border border-slate-800 h-[600px] flex flex-col sticky top-8">
                <div className="p-4 border-b border-slate-800 flex items-center gap-3">
                  <div className="w-10 h-10 bg-indigo-600 rounded-full flex items-center justify-center">
                    <MessageSquare className="w-5 h-5 text-white" />
                  </div>
                  <h3 className="font-bold text-white">Migration Copilot</h3>
                </div>
                <div className="flex-1 p-4 overflow-y-auto space-y-4">
                  {chatMessages.map((msg, i) => (
                    <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                      <div className={`max-w-[85%] p-3 rounded-2xl text-sm ${msg.role === 'user' ? 'bg-indigo-600 text-white rounded-br-none' : 'bg-slate-800 text-slate-200 border border-slate-700 rounded-bl-none'}`}>
                        {msg.content}
                      </div>
                    </div>
                  ))}
                  {isTyping && (
                    <div className="flex justify-start">
                      <div className="bg-slate-800 p-3 rounded-2xl rounded-bl-none border border-slate-700 flex items-center gap-1">
                        <div className="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce"></div>
                        <div className="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce delay-100"></div>
                        <div className="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce delay-200"></div>
                      </div>
                    </div>
                  )}
                </div>
                <div className="p-4 border-t border-slate-800">
                  <div className="relative">
                    <input
                      type="text"
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                      placeholder="Ask about errors, summary..."
                      className="w-full bg-slate-800 text-white border border-slate-700 rounded-full py-3 pl-4 pr-12 focus:outline-none focus:border-indigo-500 text-sm"
                    />
                    <button onClick={handleSendMessage} disabled={!chatInput.trim() || isTyping} className="absolute right-2 top-2 p-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-full disabled:opacity-50">
                      <Send className="w-4 h-4 ml-0.5" />
                    </button>
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
