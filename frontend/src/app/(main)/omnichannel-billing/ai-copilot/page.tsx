'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import apiClient, { isApiError } from '@/lib/apiClient';

interface Customer {
  id: string;
  name: string;
}

interface FraudAlert {
  id: string;
  alert_type: string;
  severity: string;
  alert_details: string;
  status: string;
}

interface RiskScore {
  risk_score: number;
  risk_category: string;
  delay_probability_percent: number;
  recommended_credit_limit: number;
  factors: string[];
}

export default function AICopilotPage() {
  const [alerts, setAlerts] = useState<FraudAlert[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState('');
  const [riskScore, setRiskScore] = useState<RiskScore | null>(null);
  const [error, setError] = useState('');
  const [loadingRisk, setLoadingRisk] = useState(false);

  useEffect(() => {
    Promise.all([
      apiClient.get('/api/v1/omnichannel-billing/ai/fraud-scan'),
      apiClient.get('/api/v1/omnichannel-billing/customers/'),
    ])
      .then(([alertRes, custRes]) => {
        setAlerts(alertRes.data.items || []);
        setCustomers(custRes.data.items || []);
      })
      .catch(() => setError('Failed to load AI billing copilot'));
  }, []);

  const handleCheckRisk = async () => {
    if (!selectedCustomer) return;
    setLoadingRisk(true);
    setError('');
    try {
      const res = await apiClient.get(`/api/v1/omnichannel-billing/ai/risk-score/${selectedCustomer}`);
      setRiskScore(res.data);
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to compute risk score');
    } finally {
      setLoadingRisk(false);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/omnichannel-billing/analytics/dashboard" className="text-blue-600 hover:underline text-sm mb-2 block">&larr; Back to Billing Dashboard</Link>
          <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-500 to-purple-600">
            AI Billing Copilot
          </h1>
          <p className="text-gray-600 dark:text-gray-400">Advisory intelligence for risk and fraud detection.</p>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 relative overflow-hidden">
          <div className="absolute top-0 left-0 w-1 h-full bg-red-500"></div>
          <h3 className="text-lg font-bold mb-2">Fraud Detection Alerts</h3>
          {alerts.length === 0 ? (
            <p className="text-sm text-gray-500 mb-4">No active anomalies detected in current billing cycles.</p>
          ) : (
            <ul className="space-y-2 mb-4">
              {alerts.map((a) => (
                <li key={a.id} className="text-sm p-2 bg-red-50 dark:bg-red-900/20 rounded border border-red-100 dark:border-red-800">
                  <span className="font-semibold">{a.alert_type}</span> ({a.severity}): {a.alert_details}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 relative overflow-hidden">
          <div className="absolute top-0 left-0 w-1 h-full bg-purple-500"></div>
          <h3 className="text-lg font-bold mb-2">Customer Credit Risk</h3>
          <div className="flex gap-2 mb-4">
            <select value={selectedCustomer} onChange={(e) => setSelectedCustomer(e.target.value)} className="flex-1 p-2 border rounded dark:bg-gray-700 dark:border-gray-600 text-sm">
              <option value="">- Select customer -</option>
              {customers.map((c) => (<option key={c.id} value={c.id}>{c.name}</option>))}
            </select>
            <button onClick={handleCheckRisk} disabled={!selectedCustomer || loadingRisk} className="bg-purple-600 text-white px-4 py-2 rounded text-sm hover:bg-purple-700 transition-colors shadow disabled:opacity-50">
              {loadingRisk ? 'Checking...' : 'Check Risk'}
            </button>
          </div>
          {riskScore && (
            <div className="text-sm space-y-1 p-3 bg-purple-50 dark:bg-purple-900/20 rounded border border-purple-100 dark:border-purple-800">
              <p><strong>Risk Score:</strong> {riskScore.risk_score}/100 ({riskScore.risk_category})</p>
              <p><strong>Delay Probability:</strong> {riskScore.delay_probability_percent}%</p>
              <p><strong>Recommended Credit Limit:</strong> ${Number(riskScore.recommended_credit_limit).toLocaleString()}</p>
              {riskScore.factors.length > 0 && <p><strong>Factors:</strong> {riskScore.factors.join(', ')}</p>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
