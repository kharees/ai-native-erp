'use client';

import { useEffect, useState } from 'react';
import LogoutButton from '@/components/LogoutButton';
import apiClient from '@/lib/apiClient';

interface DashboardMetrics {
  revenue: number;
  activeUsers: number;
  inventoryItems: number;
  activity: Record<string, unknown>[];
}

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<DashboardMetrics>({
    revenue: 0,
    activeUsers: 0,
    inventoryItems: 0,
    activity: []
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const [financeRes, usersRes, inventoryRes, auditRes] = await Promise.all([
          apiClient.get('/api/v1/finance-reports/dashboard-summary'),
          apiClient.get('/api/v1/users/'),
          apiClient.get('/api/v1/universal-reports/summary'),
          apiClient.get('/api/v1/audit/?limit=5')
        ]);

        setMetrics({
          revenue: financeRes.data.revenue || 0,
          activeUsers: Array.isArray(usersRes.data) ? usersRes.data.length : 0,
          inventoryItems: inventoryRes.data.total_items || inventoryRes.data.total_quantity || 0,
          activity: auditRes.data || []
        });
      } catch (err) {
        console.error('Error fetching dashboard data:', err);
        setError('Failed to load dashboard metrics. Check API connections.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  return (
    <div className="container">
      <header className="dashboard-header">
        <div>
          <h1>Dashboard</h1>
          <p>Overview of your enterprise metrics</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <LogoutButton />
        </div>
      </header>
      
      {error && <div style={{ color: 'red', marginBottom: '1rem', padding: '1rem', background: '#ffebee', borderRadius: '4px' }}>{error}</div>}

      <div className="metric-grid">
        <div className="metric-card">
          <h3>Total Revenue</h3>
          <p>{isLoading ? '...' : `$${metrics.revenue.toLocaleString()}`}</p>
        </div>
        <div className="metric-card">
          <h3>Active Users</h3>
          <p>{isLoading ? '...' : metrics.activeUsers.toLocaleString()}</p>
        </div>
        <div className="metric-card">
          <h3>Inventory Items</h3>
          <p>{isLoading ? '...' : metrics.inventoryItems.toLocaleString()}</p>
        </div>
      </div>

      <div className="activity-card" style={{ marginTop: '2rem' }}>
        <h2>Recent Activity</h2>
        <div className="activity-list">
          {isLoading ? (
            <p style={{ padding: '1rem', color: 'var(--text-muted)' }}>Loading activity...</p>
          ) : metrics.activity.length === 0 ? (
            <p style={{ padding: '1rem', color: 'var(--text-muted)' }}>No recent activity found.</p>
          ) : (
            metrics.activity.map((log: Record<string, unknown>, index: number) => (
              <div key={(log.id as string) || index} className="activity-item" style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '1rem', borderBottom: '1px solid var(--border)' }}>
                <div className="avatar" style={{ width: '40px', height: '40px', borderRadius: '50%', background: 'var(--primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: 'bold' }}>
                  {((log.action_category as string) || 'A').substring(0, 1)}
                </div>
                <div className="activity-details" style={{ flex: 1 }}>
                  <p style={{ margin: 0, fontWeight: 500 }}>
                    {log.action_category as string} - {log.action_type as string}
                  </p>
                  <p className="time" style={{ margin: 0, fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                    {new Date(log.created_at as string).toLocaleString()}
                  </p>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
