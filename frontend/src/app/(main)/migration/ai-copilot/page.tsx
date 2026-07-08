'use client';

import React, { useState } from 'react';
import { 
  Sparkles, Activity, ShieldAlert, HeartPulse, ShieldCheck, 
  Search, Wand2, MessageSquare, Send, CheckCircle, XCircle
} from 'lucide-react';

export default function MigrationAICopilotPage() {
  const [chatMessages, setChatMessages] = useState<{role: 'user'|'ai', content: string}[]>([
    { role: 'ai', content: "Hi! I'm your Migration AI Copilot. I can analyze errors, suggest data cleansing rules, and answer questions about your import session. How can I help?" }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);

  // Mock Metrics
  const healthScore = 92;
  const riskScore = 8;
  const dataQualityMetrics = [
    { category: 'Format Issues', count: 42, impact: 'HIGH', desc: 'Invalid emails or phone numbers.' },
    { category: 'Duplicates', count: 2500, impact: 'MEDIUM', desc: 'Potential duplicate records detected.' }
  ];
  const cleansingSuggestions = [
    { id: '1', type: 'MERGE_DUPLICATES', title: 'Merge duplicate emails', affected: 2500, conf: 95 },
    { id: '2', type: 'NORMALIZE_FORMAT', title: 'Standardize phone numbers to E.164', affected: 7500, conf: 88 }
  ];

  const handleSendMessage = () => {
    if (!chatInput.trim()) return;
    
    setChatMessages(prev => [...prev, { role: 'user', content: chatInput }]);
    const query = chatInput.toLowerCase();
    setChatInput('');
    setIsTyping(true);

    setTimeout(() => {
      let response = "I'm sorry, I couldn't understand that. Could you ask about errors, duplicates, or a summary?";
      if (query.includes('error') || query.includes('fail')) {
        response = "There are 42 failed records. The primary root cause is missing mandatory fields. Would you like me to suggest some cleansing rules?";
      } else if (query.includes('duplicate')) {
        response = "Based on my analysis, about 5% (2,500) of your records might be duplicates. I highly recommend applying the 'Merge duplicate emails' cleansing rule.";
      } else if (query.includes('summary')) {
        response = "Overall Migration Health is strong at 92%. However, there's an 8% risk score primarily driven by format issues. Please review the AI Recommendations panel.";
      }
      
      setChatMessages(prev => [...prev, { role: 'ai', content: response }]);
      setIsTyping(false);
    }, 1500);
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 p-8 font-sans text-slate-800 dark:text-slate-200">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Header */}
        <header className="flex items-center justify-between bg-white dark:bg-slate-800 p-6 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-3">
              <Sparkles className="w-7 h-7 text-indigo-500" />
              AI Migration Copilot
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Advisory intelligence for data quality, automated field mapping, and deep error analysis.
            </p>
          </div>
          <div className="flex gap-4">
            <span className="px-4 py-2 bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400 rounded-lg font-bold flex items-center gap-2 shadow-sm">
              <ShieldCheck className="w-4 h-4" /> Advisory Mode Active
            </span>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Main Content Area */}
          <div className="lg:col-span-2 space-y-8">
            
            {/* Health & Risk Metrics */}
            <div className="grid grid-cols-2 gap-6">
              <div className="bg-white dark:bg-slate-800 p-6 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700">
                <div className="flex justify-between items-start mb-2">
                  <div className="p-3 bg-green-100 dark:bg-green-900/30 text-green-600 rounded-xl">
                    <HeartPulse className="w-6 h-6" />
                  </div>
                  <span className="text-sm font-semibold text-green-600">Healthy</span>
                </div>
                <p className="text-sm font-bold text-slate-500 mt-4">Migration Health Score</p>
                <p className="text-4xl font-black text-slate-900 dark:text-white mt-1">{healthScore}/100</p>
              </div>

              <div className="bg-white dark:bg-slate-800 p-6 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700">
                <div className="flex justify-between items-start mb-2">
                  <div className="p-3 bg-amber-100 dark:bg-amber-900/30 text-amber-600 rounded-xl">
                    <Activity className="w-6 h-6" />
                  </div>
                  <span className="text-sm font-semibold text-amber-600">Moderate Risk</span>
                </div>
                <p className="text-sm font-bold text-slate-500 mt-4">Import Risk Score</p>
                <p className="text-4xl font-black text-slate-900 dark:text-white mt-1">{riskScore}/100</p>
              </div>
            </div>

            {/* AI Data Quality Report */}
            <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
              <h2 className="text-lg font-bold flex items-center gap-2 mb-6"><Search className="text-indigo-500"/> AI Data Quality Diagnostics</h2>
              <div className="space-y-4">
                {dataQualityMetrics.map((metric, i) => (
                  <div key={i} className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-900 rounded-xl border border-slate-100 dark:border-slate-800">
                    <div className="flex items-center gap-4">
                      <div className={`p-2 rounded-full ${metric.impact === 'HIGH' ? 'bg-red-100 text-red-600' : 'bg-amber-100 text-amber-600'}`}>
                        <ShieldAlert className="w-5 h-5" />
                      </div>
                      <div>
                        <h4 className="font-bold">{metric.category}</h4>
                        <p className="text-sm text-slate-500">{metric.desc}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="text-xl font-bold">{metric.count.toLocaleString()}</span>
                      <p className="text-xs text-slate-500">Issues found</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* AI Recommendations */}
            <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-lg font-bold flex items-center gap-2"><Wand2 className="text-indigo-500"/> AI Cleansing Recommendations</h2>
                <span className="text-xs font-semibold bg-blue-100 text-blue-700 px-3 py-1 rounded-full">Requires Approval</span>
              </div>
              <div className="space-y-4">
                {cleansingSuggestions.map((sug, i) => (
                  <div key={i} className="p-5 border border-indigo-100 dark:border-indigo-900/50 bg-indigo-50/50 dark:bg-indigo-900/10 rounded-xl flex items-center justify-between">
                    <div>
                      <h4 className="font-bold text-indigo-900 dark:text-indigo-300">{sug.title}</h4>
                      <p className="text-sm text-slate-500 mt-1">Affects <span className="font-semibold text-slate-700 dark:text-slate-300">{sug.affected.toLocaleString()}</span> records.</p>
                      <div className="mt-3 flex items-center gap-2 text-xs font-bold text-indigo-600 dark:text-indigo-400">
                        <Sparkles className="w-3 h-3" /> {sug.conf}% AI Confidence
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button className="p-2 bg-white dark:bg-slate-800 hover:bg-green-50 text-green-600 border border-slate-200 dark:border-slate-700 rounded-lg transition-colors" title="Accept & Apply">
                        <CheckCircle className="w-5 h-5" />
                      </button>
                      <button className="p-2 bg-white dark:bg-slate-800 hover:bg-red-50 text-red-600 border border-slate-200 dark:border-slate-700 rounded-lg transition-colors" title="Reject">
                        <XCircle className="w-5 h-5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

          </div>

          {/* AI Chat Assistant Sidebar */}
          <div className="lg:col-span-1">
            <div className="bg-slate-900 rounded-2xl shadow-lg border border-slate-800 h-[800px] flex flex-col sticky top-8">
              <div className="p-4 border-b border-slate-800 flex items-center gap-3">
                <div className="w-10 h-10 bg-indigo-600 rounded-full flex items-center justify-center">
                  <MessageSquare className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="font-bold text-white">Migration Copilot</h3>
                  <span className="flex items-center gap-1 text-xs text-indigo-400 font-medium">
                    <span className="w-2 h-2 rounded-full bg-green-500"></span> Online
                  </span>
                </div>
              </div>

              <div className="flex-1 p-4 overflow-y-auto space-y-4 scrollbar-thin">
                {chatMessages.map((msg, i) => (
                  <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[85%] p-3 rounded-2xl text-sm ${msg.role === 'user' ? 'bg-indigo-600 text-white rounded-br-none' : 'bg-slate-800 text-slate-200 border border-slate-700 rounded-bl-none'}`}>
                      {msg.role === 'ai' && <Sparkles className="w-3 h-3 text-indigo-400 mb-1 inline-block mr-1" />}
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
      </div>
    </div>
  );
}
