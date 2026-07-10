'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import apiClient, { isApiError } from '@/lib/apiClient';
import { useAuthStore } from '@/store/authStore';

interface Session {
  id: string;
  session_status: string;
  opening_balance: number;
  opened_at: string;
}

interface HoldBill {
  id: string;
  session_id: string;
  reference_name: string | null;
  cart_data: Record<string, unknown>;
}

const BASE = '/api/v1/omnichannel-billing/pos';

export default function POSPage() {
  const userId = useAuthStore((s) => s.user?.id);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [holdBills, setHoldBills] = useState<HoldBill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [openingBalance, setOpeningBalance] = useState('0');
  const [holdReference, setHoldReference] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([apiClient.get(`${BASE}/sessions`), apiClient.get(`${BASE}/hold-bills`)])
      .then(([sessionRes, holdRes]) => {
        setSessions(sessionRes.data.items || []);
        setHoldBills(holdRes.data.items || []);
      })
      .catch(() => setError('Failed to load POS data'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const activeSession = sessions.find((s) => s.session_status === 'OPEN');

  const handleStartSession = async () => {
    if (!userId) return;
    setError('');
    try {
      await apiClient.post(`${BASE}/sessions`, { user_id: userId, opening_balance: parseFloat(openingBalance) || 0 });
      load();
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to start session');
    }
  };

  const handleHoldBill = async () => {
    if (!activeSession) return;
    setError('');
    try {
      await apiClient.post(`${BASE}/hold-bills`, {
        session_id: activeSession.id,
        reference_name: holdReference || null,
        cart_data: {},
      });
      setHoldReference('');
      load();
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to hold bill');
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900 flex flex-col">
      <header className="bg-blue-600 text-white p-4 flex justify-between items-center shadow-md">
        <div>
          <Link href="/omnichannel-billing/analytics/dashboard" className="hover:underline text-sm opacity-80">&larr; Dashboard</Link>
          <h1 className="text-xl font-bold">POS Terminal - Universal Billing</h1>
        </div>
        <div className="flex items-center space-x-4">
          {activeSession ? (
            <span className="bg-green-500 px-3 py-1 rounded text-sm font-semibold">Session Open (Balance: {activeSession.opening_balance})</span>
          ) : (
            <>
              <input
                type="number"
                step="0.01"
                value={openingBalance}
                onChange={(e) => setOpeningBalance(e.target.value)}
                placeholder="Opening balance"
                className="w-32 p-1 rounded text-gray-900 text-sm"
              />
              <button onClick={handleStartSession} className="bg-blue-500 hover:bg-blue-700 px-3 py-1 rounded">Start Session</button>
            </>
          )}
        </div>
      </header>

      <main className="flex-1 flex p-4 space-x-4">
        <div className="w-2/3 bg-white dark:bg-gray-800 rounded-lg shadow p-4 border border-gray-200 dark:border-gray-700 flex flex-col">
          <h2 className="text-lg font-bold mb-4 border-b pb-2">Held Bills</h2>
          {error && <p className="text-sm text-red-600 mb-2">{error}</p>}
          {loading ? (
            <p className="text-gray-400">Loading...</p>
          ) : holdBills.length === 0 ? (
            <div className="flex-1 flex items-center justify-center text-gray-400">No bills on hold.</div>
          ) : (
            <ul className="space-y-2">
              {holdBills.map((h) => (
                <li key={h.id} className="p-3 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 text-sm">
                  {h.reference_name || `Bill ${h.id.slice(0, 8)}`}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="w-1/3 bg-white dark:bg-gray-800 rounded-lg shadow p-4 border border-gray-200 dark:border-gray-700 flex flex-col">
          <h2 className="text-lg font-bold mb-4 border-b pb-2">Hold Current Bill</h2>
          <input
            type="text"
            placeholder="Reference name (optional)"
            value={holdReference}
            onChange={(e) => setHoldReference(e.target.value)}
            className="w-full p-3 border rounded mb-4 bg-gray-50 dark:bg-gray-900 dark:text-white"
            disabled={!activeSession}
          />
          <button
            onClick={handleHoldBill}
            disabled={!activeSession}
            className="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-3 rounded shadow-lg transition-colors disabled:opacity-50"
          >
            {activeSession ? 'Hold Bill' : 'Start a session to hold bills'}
          </button>
        </div>
      </main>
    </div>
  );
}
