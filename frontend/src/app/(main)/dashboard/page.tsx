'use client';

import { useEffect, useState } from 'react';
import LogoutButton from '@/components/LogoutButton';
import apiClient, { isApiError } from '@/lib/apiClient';
import { formatCurrency } from '@/lib/formatCurrency';
import {
  Card,
  PageShell,
  Badge,
  StatCard,
  SkeletonText
} from '@/components/ui';
import { TrendingUp, Users, Package, Activity } from 'lucide-react';

interface DashboardMetrics {
  revenue: number | string;
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
  // One entry per failed widget, e.g. "Could not load revenue data" --
  // not a single catch-all string. A dashboard firing 4 independent calls
  // must let 3 succeed and show real data even if the 4th fails, and must
  // say which one failed and why (see the console.error alongside each
  // entry below) rather than one generic "Check API connections." banner
  // that gives no indication of which endpoint broke or how.
  const [errors, setErrors] = useState<string[]>([]);

  useEffect(() => {
    const fetchDashboardData = async () => {
      const [financeRes, usersRes, inventoryRes, auditRes] = await Promise.allSettled([
        apiClient.get('/api/v1/finance-reports/dashboard-summary'),
        apiClient.get('/api/v1/users/'),
        apiClient.get('/api/v1/universal-reports/summary'),
        apiClient.get('/api/v1/audit/?limit=5'),
      ]);

      const failures: string[] = [];

      // Logs the specific endpoint, status code, and response body for
      // whichever call failed -- console.error, not just the vague
      // network error axios itself would print, so a dev looking at the
      // console can immediately tell which of the 4 broke and why.
      const logFailure = (endpoint: string, err: unknown) => {
        if (isApiError(err)) {
          console.error(`Dashboard widget failed: ${endpoint}`, { status: err.status, body: err.detail ?? err.message });
        } else {
          console.error(`Dashboard widget failed: ${endpoint}`, err);
        }
      };

      // Computed directly from the settled results (not inside a setState
      // updater callback) -- React 18 StrictMode invokes updater functions
      // twice in dev specifically to catch impure ones, and the push()/
      // console.error side effects here used to live inside a
      // setMetrics(prev => ...) updater, so every failed widget's message
      // got appended twice (8 lines instead of 4 on a full failure).
      const next: DashboardMetrics = { revenue: 0, activeUsers: 0, inventoryItems: 0, activity: [] };

      if (financeRes.status === 'fulfilled') {
        next.revenue = financeRes.value.data.revenue || 0;
      } else {
        logFailure('/api/v1/finance-reports/dashboard-summary', financeRes.reason);
        failures.push('Could not load revenue data.');
      }

      if (usersRes.status === 'fulfilled') {
        next.activeUsers = Array.isArray(usersRes.value.data) ? usersRes.value.data.length : 0;
      } else {
        logFailure('/api/v1/users/', usersRes.reason);
        failures.push('Could not load active user count.');
      }

      if (inventoryRes.status === 'fulfilled') {
        next.inventoryItems = inventoryRes.value.data.total_items || inventoryRes.value.data.total_quantity || 0;
      } else {
        logFailure('/api/v1/universal-reports/summary', inventoryRes.reason);
        failures.push('Could not load inventory data.');
      }

      if (auditRes.status === 'fulfilled') {
        next.activity = auditRes.value.data || [];
      } else {
        logFailure('/api/v1/audit/?limit=5', auditRes.reason);
        failures.push('Could not load recent activity.');
      }

      setMetrics(next);
      setErrors(failures);
      setIsLoading(false);
    };

    fetchDashboardData();
  }, []);

  return (
    <PageShell 
      title="Dashboard" 
      actions={<LogoutButton />}
    >
      <div className="space-y-6 max-w-7xl">
        {errors.length > 0 && (
          <div className="flex items-start gap-3 px-4 py-3 rounded-lg bg-danger-light border border-danger/20 text-danger-dark text-body">
            <span aria-hidden className="mt-0.5">⚠</span>
            <ul className="space-y-0.5">
              {errors.map((message) => (
                <li key={message}>{message}</li>
              ))}
            </ul>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <StatCard
            data-testid="stat-revenue"
            label="Total Revenue"
            value={isLoading ? <SkeletonText lines={1} className="w-24 mt-2" /> : formatCurrency(metrics.revenue, { whole: true })}
            icon={<TrendingUp size={18} />}
          />
          <StatCard
            label="Active Users"
            value={isLoading ? <SkeletonText lines={1} className="w-24 mt-2" /> : metrics.activeUsers.toLocaleString()}
            icon={<Users size={18} />}
          />
          <StatCard
            label="Inventory Items"
            value={isLoading ? <SkeletonText lines={1} className="w-24 mt-2" /> : metrics.inventoryItems.toLocaleString()}
            icon={<Package size={18} />}
          />
        </div>

        <Card>
          <div className="px-4 py-3 border-b border-neutral-200 dark:border-neutral-800 flex items-center gap-2">
            <Activity size={16} className="text-neutral-400" aria-hidden />
            <h2 className="text-card-title text-neutral-900 dark:text-neutral-100">Recent Activity</h2>
          </div>
          <div className="divide-y divide-neutral-200 dark:divide-neutral-800">
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="flex items-center gap-4 px-4 py-3">
                  <div className="w-8 h-8 rounded-full bg-neutral-200 dark:bg-neutral-800 animate-pulse shrink-0" />
                  <div className="flex-1 space-y-1.5">
                    <SkeletonText lines={1} className="w-1/2" />
                    <SkeletonText lines={1} className="w-1/4" />
                  </div>
                </div>
              ))
            ) : metrics.activity.length === 0 ? (
              <div className="px-4 py-12 text-center text-body text-neutral-500">
                No recent activity found.
              </div>
            ) : (
              metrics.activity.map((log: Record<string, unknown>, index: number) => {
                const id       = log.id       != null ? String(log.id)       : String(index);
                const category = log.action_category != null ? String(log.action_category) : '';
                const type_    = log.action_type     != null ? String(log.action_type)     : '';
                const ts       = log.created_at      != null ? String(log.created_at)      : '';
                return (
                  <div
                    key={id}
                    className="flex items-center gap-4 px-4 py-3 hover:bg-neutral-50 dark:hover:bg-neutral-800/50 transition-colors"
                  >
                    <div className="w-8 h-8 rounded-full bg-accent-600 flex items-center justify-center text-white text-caption font-semibold shrink-0">
                      {(category || 'A').substring(0, 1).toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-body text-neutral-900 dark:text-neutral-200 font-medium truncate">
                        {category}
                        {type_ ? ` — ${type_}` : ''}
                      </p>
                      <p className="text-caption text-neutral-500 dark:text-neutral-400 mt-0.5">
                        {ts ? new Date(ts).toLocaleString() : ''}
                      </p>
                    </div>
                    {category && (
                      <Badge variant="neutral" className="shrink-0 hidden sm:inline-flex">
                        {category}
                      </Badge>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </Card>
      </div>
    </PageShell>
  );
}
