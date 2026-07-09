/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";
import React, { useState, useEffect } from 'react';

export default function RiskDashboardPage() {
  const [insights, setInsights] = useState<any[]>([]);

  useEffect(() => {
    // Mock API Call to GET /api/v1/finance-ai/insights
    setTimeout(() => {
      setInsights([
        { id: '1', type: 'FRAUD_RISK', title: 'Suspicious Duplicate Entry Detection', desc: 'Detected two identical vendor payments of $15,000 on the same date.', severity: 'CRITICAL', confidence: 94.5, status: 'PENDING' },
        { id: '2', type: 'COMPLIANCE', title: 'Missing Approval Workflow', desc: 'Journal Voucher #JV-2026-0045 lacks secondary manager approval despite exceeding the $10,000 threshold.', severity: 'HIGH', confidence: 99.9, status: 'PENDING' },
        { id: '3', type: 'SUGGESTION', title: 'Bank Reconciliation Match', desc: 'Found a 98% fuzzy match for unmatched bank transaction ID #892 against an open AP Bill.', severity: 'LOW', confidence: 98.0, status: 'APPROVED' }
      ]);
    }, 500);
  }, []);

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6 border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold">Fraud & Risk Dashboard</h1>
          <p className="text-gray-500 text-sm">Automated Anomaly Detection</p>
        </div>
        <button className="bg-red-600 text-white px-4 py-2 rounded shadow hover:bg-red-700 font-medium">Run Deep Scan</button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <p className="text-gray-500 text-sm">System Health Score</p>
          <p className="text-4xl font-bold text-green-600">92%</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <p className="text-gray-500 text-sm">Pending Critical Alerts</p>
          <p className="text-4xl font-bold text-red-600">1</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <p className="text-gray-500 text-sm">Unmatched Transactions</p>
          <p className="text-4xl font-bold text-orange-500">14</p>
        </div>
      </div>

      <h2 className="text-lg font-bold mb-4 text-gray-800">Actionable AI Insights</h2>
      <div className="space-y-4">
        {insights.map((item) => (
          <div key={item.id} className="bg-white p-5 rounded-lg shadow-sm border-l-4 border-gray-200 flex flex-col md:flex-row justify-between items-start md:items-center"
               style={{ borderLeftColor: item.severity === 'CRITICAL' ? '#ef4444' : item.severity === 'HIGH' ? '#f97316' : '#3b82f6' }}>
            <div className="mb-4 md:mb-0">
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-xs font-bold px-2 py-1 rounded text-white ${item.severity === 'CRITICAL' ? 'bg-red-500' : item.severity === 'HIGH' ? 'bg-orange-500' : 'bg-blue-500'}`}>
                  {item.type}
                </span>
                <h3 className="font-bold text-gray-900">{item.title}</h3>
                <span className="text-xs text-gray-400 bg-gray-100 px-2 rounded">Confidence: {item.confidence}%</span>
              </div>
              <p className="text-gray-600 text-sm mt-2">{item.desc}</p>
            </div>
            
            <div className="flex gap-2 shrink-0">
              {item.status === 'PENDING' ? (
                <>
                  <button className="px-3 py-1 bg-gray-100 text-gray-700 text-sm font-medium rounded hover:bg-gray-200">Dismiss</button>
                  <button className="px-3 py-1 bg-blue-600 text-white text-sm font-medium rounded hover:bg-blue-700">Investigate</button>
                </>
              ) : (
                <span className="text-sm font-bold text-green-600 bg-green-50 px-3 py-1 rounded border border-green-200">Resolved</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
