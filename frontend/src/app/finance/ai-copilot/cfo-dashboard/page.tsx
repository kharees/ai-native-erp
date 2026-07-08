"use client";
import React from 'react';

export default function CFODashboardPage() {
  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-6 border-b pb-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">AI CFO Dashboard</h1>
          <p className="text-gray-500">Executive Summary & Predictive Insights</p>
        </div>
        <div className="flex gap-2">
          <button className="bg-white border text-gray-700 px-4 py-2 rounded shadow hover:bg-gray-50">Generate Report</button>
          <button className="bg-indigo-600 text-white px-4 py-2 rounded shadow hover:bg-indigo-700">Ask Copilot</button>
        </div>
      </div>

      {/* KPI Section */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        {[
          { label: 'Revenue YTD', val: '$1.25M', trend: '+12%', color: 'text-green-600' },
          { label: 'Net Profit Margin', val: '28%', trend: '+2.5%', color: 'text-green-600' },
          { label: 'OpEx vs Budget', val: '105%', trend: 'Over Budget', color: 'text-red-600' },
          { label: 'Cash Runway', val: '14 mo', trend: 'Stable', color: 'text-blue-600' }
        ].map((kpi, idx) => (
          <div key={idx} className="bg-white p-5 rounded-lg shadow-sm border border-gray-200">
            <p className="text-sm font-medium text-gray-500 mb-1">{kpi.label}</p>
            <p className="text-3xl font-bold text-gray-900 mb-2">{kpi.val}</p>
            <p className={`text-xs font-bold ${kpi.color}`}>{kpi.trend}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* AI Recommendations */}
        <div className="lg:col-span-2 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
            <span className="text-indigo-600">💡</span> AI Recommendations
          </h2>
          <div className="space-y-4">
            <div className="p-4 bg-indigo-50 rounded border border-indigo-100">
              <h3 className="font-bold text-indigo-900 mb-1">Optimize Idle Cash</h3>
              <p className="text-sm text-indigo-800">Your operating account balance exceeds required working capital by $200k. Consider transferring to a short-term yield account.</p>
            </div>
            <div className="p-4 bg-orange-50 rounded border border-orange-100">
              <h3 className="font-bold text-orange-900 mb-1">Receivables Collection Risk</h3>
              <p className="text-sm text-orange-800">Average collection period has increased to 45 days. Suggest activating automated dunning emails for 3 flagged clients.</p>
            </div>
          </div>
        </div>

        {/* Financial Health Score */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 flex flex-col items-center justify-center text-center">
          <h2 className="text-lg font-bold mb-2">Overall Financial Health</h2>
          <div className="relative w-40 h-40 flex items-center justify-center">
            {/* Mock Donut Chart CSS */}
            <div className="absolute inset-0 rounded-full border-8 border-gray-100"></div>
            <div className="absolute inset-0 rounded-full border-8 border-green-500" style={{ clipPath: 'polygon(0 0, 100% 0, 100% 100%, 0 100%)', transform: 'rotate(45deg)' }}></div>
            <div className="z-10 flex flex-col">
              <span className="text-4xl font-black text-gray-800">A-</span>
              <span className="text-xs text-gray-500 uppercase mt-1">Excellent</span>
            </div>
          </div>
          <p className="text-sm text-gray-500 mt-4">Based on liquidity, profitability, and solvency ratios derived from the GL.</p>
        </div>
      </div>
    </div>
  );
}
