'use client';

import { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import apiClient, { isApiError } from '@/lib/apiClient';

interface Message {
  role: 'user' | 'bot';
  text: string;
}

const SUGGESTIONS = ['Show low stock items', 'Show dead stock', 'What products should I reorder?'];

export default function CopilotPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'bot',
      text: 'Hello! I am your Universal Inventory AI Copilot. I can help you forecast demand, optimize safety stock, or identify risky inventory. What would you like to explore?',
    },
  ]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const send = async (query: string) => {
    if (!query.trim() || sending) return;
    setMessages((prev) => [...prev, { role: 'user', text: query }]);
    setInput('');
    setSending(true);
    setError('');
    try {
      const res = await apiClient.post('/api/v1/universal-intelligence/copilot/ask', { query });
      setMessages((prev) => [...prev, { role: 'bot', text: res.data.response_text }]);
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to reach the AI copilot');
    } finally {
      setSending(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    send(input);
  };

  return (
    <div className="p-8 max-w-4xl mx-auto h-[calc(100vh-4rem)] flex flex-col">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/universal-inventory/intelligence" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to AI Dashboard</Link>
          <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-purple-600 to-blue-600">Inventory AI Copilot</h1>
          <p className="text-gray-500 text-sm mt-1">Ask questions about your stock, forecasts, and risks.</p>
        </div>
      </div>

      <div className="flex-1 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 flex flex-col overflow-hidden">
        <div className="flex-1 p-6 overflow-y-auto bg-gray-50 dark:bg-gray-900/50 space-y-6">
          {messages.map((m, i) => (
            <div key={i} className={`flex gap-4 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white font-bold shrink-0 ${m.role === 'user' ? 'bg-blue-600' : 'bg-purple-600'}`}>
                {m.role === 'user' ? 'U' : 'AI'}
              </div>
              <div
                className={
                  m.role === 'user'
                    ? 'bg-blue-600 text-white p-4 rounded-lg rounded-tr-none shadow-sm max-w-[80%]'
                    : 'bg-white dark:bg-gray-800 p-4 rounded-lg rounded-tl-none border border-gray-200 dark:border-gray-700 shadow-sm max-w-[80%]'
                }
              >
                <p className="text-sm">{m.text}</p>
                {m.role === 'bot' && i === 0 && (
                  <div className="mt-4 flex flex-wrap gap-2">
                    {SUGGESTIONS.map((s) => (
                      <span
                        key={s}
                        onClick={() => send(s)}
                        className="text-xs bg-gray-100 dark:bg-gray-700 px-3 py-1 rounded-full cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-600"
                      >
                        &quot;{s}&quot;
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          {sending && <p className="text-xs text-gray-500 pl-12">AI Copilot is thinking...</p>}
          {error && <p className="text-xs text-red-600 pl-12">{error}</p>}
          <div ref={bottomRef} />
        </div>

        <form onSubmit={handleSubmit} className="p-4 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Ask about your inventory..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              className="flex-1 p-3 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
            <button type="submit" disabled={sending} className="bg-purple-600 text-white px-6 py-3 rounded-lg shadow hover:bg-purple-700 transition-colors font-semibold disabled:opacity-50">
              Send
            </button>
          </div>
          <p className="text-xs text-gray-400 mt-2 text-center">AI recommendations are advisory only. Human approval is required for all stock movements.</p>
        </form>
      </div>
    </div>
  );
}
