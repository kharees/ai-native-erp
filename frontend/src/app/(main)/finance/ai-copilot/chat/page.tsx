'use client';

import { useState } from 'react';
import apiClient, { isApiError } from '@/lib/apiClient';

interface Message {
  role: 'system' | 'user' | 'ai';
  text: string;
}

export default function CopilotChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'system', text: 'Hello, CFO. I am your AI Finance Copilot. How can I assist you today?' },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    const prompt = input;
    setMessages((prev) => [...prev, { role: 'user', text: prompt }]);
    setInput('');
    setLoading(true);
    setError('');
    try {
      const res = await apiClient.post('/api/v1/finance-ai/chat', { prompt });
      setMessages((prev) => [...prev, { role: 'ai', text: res.data.response }]);
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to reach the AI copilot');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto flex flex-col h-[85vh]">
      <div className="mb-4 border-b pb-4">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <span className="text-blue-600">✨</span> AI CFO Copilot
        </h1>
        <p className="text-gray-500 text-sm">Advisory Only. I cannot post Journal Entries.</p>
      </div>

      <div className="flex-1 overflow-y-auto bg-gray-50 rounded-lg p-4 shadow-inner mb-4 flex flex-col gap-4 border">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[75%] rounded-lg p-4 ${msg.role === 'user' ? 'bg-blue-600 text-white shadow' : 'bg-white border text-gray-800 shadow-sm'}`}>
              <p className="text-sm leading-relaxed">{msg.text}</p>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border text-gray-800 shadow-sm rounded-lg p-4 text-sm animate-pulse">
              Analyzing ledger data...
            </div>
          </div>
        )}
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>

      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Ask me to explain the P&L, predict cash flow, or flag risks..."
          className="flex-1 border border-gray-300 rounded-lg px-4 py-3 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          className="bg-blue-600 text-white px-6 py-3 rounded-lg shadow hover:bg-blue-700 disabled:opacity-50 font-bold"
        >
          Send
        </button>
      </div>
    </div>
  );
}
