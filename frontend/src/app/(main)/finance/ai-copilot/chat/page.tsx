"use client";
import React, { useState, useEffect } from 'react';

export default function CopilotChatPage() {
  const [messages, setMessages] = useState<any[]>([
    { role: 'system', text: 'Hello, CFO. I am your AI Finance Copilot. I have analyzed the latest General Ledger data. How can I assist you today?' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSend = () => {
    if (!input.trim()) return;
    const userMessage = { role: 'user', text: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    // Mock API Call to POST /api/v1/finance-ai/chat
    setTimeout(() => {
      let responseText = "I am analyzing the General Ledger for underlying trends. Based on standard heuristics, there are no immediate compliance risks. Could you specify if you are looking for Budget Variances or Asset Depreciation forecasts?";
      
      const lowerInput = input.toLowerCase();
      if (lowerInput.includes('p&l') || lowerInput.includes('profit') || lowerInput.includes('expense')) {
        responseText = "Based on the latest GL aggregations, your Net Profit margin is currently healthy at 28%. However, operating expenses specifically in the Marketing category have increased by 30% against the Q1 Budget. I recommend reviewing the recent journal entries under the 5300 Account.";
      } else if (lowerInput.includes('overdue') || lowerInput.includes('receivable')) {
        responseText = "Currently, Accounts Receivable stands at $65,000. There are 3 major collections flagged in the 60-90 day aging bucket. Our predictive model suggests a 15% risk of bad debt if not acted upon within the next 7 days.";
      } else if (lowerInput.includes('cash flow') || lowerInput.includes('predict')) {
        responseText = "The Cash Flow Forecast model for Q3-2026 predicts a net increase to $650,000. Operating cash flow remains strong, though liquidity may tighten briefly mid-quarter due to the scheduled Property & Equipment acquisition of $150,000.";
      }

      setMessages(prev => [...prev, { role: 'ai', text: responseText }]);
      setLoading(false);
    }, 1500);
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
      </div>

      <div className="flex gap-2">
        <input 
          type="text" 
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSend()}
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
