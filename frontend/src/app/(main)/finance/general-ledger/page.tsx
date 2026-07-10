'use client';

import { useEffect, useState, useMemo } from 'react';
import apiClient from '@/lib/apiClient';

interface Account {
  id: string;
  account_code: string;
  name: string;
}

interface Line {
  id: string;
  account_id: string;
  debit: number;
  credit: number;
  description: string | null;
}

interface Voucher {
  id: string;
  voucher_number: string;
  entry_date: string;
  reference: string | null;
  status: string;
  lines: Line[];
}

export default function GeneralLedgerPage() {
  const [vouchers, setVouchers] = useState<Voucher[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedAccount, setSelectedAccount] = useState('all');

  useEffect(() => {
    Promise.all([
      apiClient.get('/api/v1/finance-core/journals'),
      apiClient.get('/api/v1/finance-core/accounts'),
    ])
      .then(([voucherRes, accountRes]) => {
        setVouchers(voucherRes.data || []);
        setAccounts(accountRes.data || []);
      })
      .catch(() => setError('Failed to load general ledger'))
      .finally(() => setLoading(false));
  }, []);

  const accountLabel = (id: string) => {
    const a = accounts.find((acc) => acc.id === id);
    return a ? `${a.name} (${a.account_code})` : id;
  };

  const entries = useMemo(() => {
    const rows: { id: string; date: string; account_id: string; description: string; debit: number; credit: number; status: string }[] = [];
    for (const v of vouchers) {
      for (const line of v.lines) {
        rows.push({
          id: line.id,
          date: v.entry_date,
          account_id: line.account_id,
          description: line.description || v.reference || v.voucher_number,
          debit: Number(line.debit),
          credit: Number(line.credit),
          status: v.status,
        });
      }
    }
    return rows
      .filter((r) => selectedAccount === 'all' || r.account_id === selectedAccount)
      .sort((a, b) => a.date.localeCompare(b.date));
  }, [vouchers, selectedAccount]);

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">General Ledger</h1>
        <div className="flex space-x-4">
          <select
            className="border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm px-4 py-2"
            value={selectedAccount}
            onChange={(e) => setSelectedAccount(e.target.value)}
          >
            <option value="all">All Accounts</option>
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>{a.name} ({a.account_code})</option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">{error}</div>
      )}

      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Account</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Description</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Debit</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Credit</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {loading ? (
              <tr><td colSpan={6} className="px-6 py-4 text-center">Loading ledger entries...</td></tr>
            ) : entries.length === 0 ? (
              <tr><td colSpan={6} className="px-6 py-4 text-center text-gray-500">No ledger entries found.</td></tr>
            ) : entries.map((entry) => (
              <tr key={entry.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{new Date(entry.date).toLocaleDateString()}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{accountLabel(entry.account_id)}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{entry.description}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900">
                  {entry.debit > 0 ? `$${entry.debit.toFixed(2)}` : '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900">
                  {entry.credit > 0 ? `$${entry.credit.toFixed(2)}` : '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{entry.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
