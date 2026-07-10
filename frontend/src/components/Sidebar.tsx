'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import styles from './Sidebar.module.css';
import {
  LayoutDashboard,
  Users,
  PackageSearch,
  Receipt,
  LineChart,
  Database,
  ChevronDown,
} from 'lucide-react';

interface NavChild {
  name: string;
  href: string;
}

interface NavItem {
  name: string;
  href: string;
  icon: React.ReactNode;
  children?: NavChild[];
}

const navItems: NavItem[] = [
  { name: 'Dashboard', href: '/dashboard', icon: <LayoutDashboard /> },
  {
    name: 'Master Foundation',
    href: '/users',
    icon: <Users />,
    children: [
      { name: 'Users', href: '/users' },
      { name: 'Organization', href: '/organization' },
      { name: 'RBAC & Roles', href: '/rbac' },
      { name: 'Audit Log', href: '/audit' },
      { name: 'Sessions', href: '/sessions' },
      { name: 'Intelligence', href: '/intelligence' },
    ],
  },
  {
    name: 'Universal Inventory',
    href: '/universal-inventory',
    icon: <PackageSearch />,
    children: [
      { name: 'Overview', href: '/universal-inventory' },
      { name: 'Items', href: '/universal-inventory/items' },
      { name: 'Categories', href: '/universal-inventory/categories' },
      { name: 'Brands', href: '/universal-inventory/brands' },
      { name: 'UOM', href: '/universal-inventory/uom' },
      { name: 'Warehouses', href: '/universal-inventory/warehouses' },
      { name: 'Warehouse Bins', href: '/universal-inventory/warehouses/bins' },
      { name: 'Stock', href: '/universal-inventory/stock' },
      { name: 'Ledger', href: '/universal-inventory/ledger' },
      { name: 'Batch Tracking', href: '/universal-inventory/tracking/batches' },
      { name: 'Expiry Tracking', href: '/universal-inventory/tracking/expiry' },
      { name: 'Serial Tracking', href: '/universal-inventory/tracking/serials' },
      { name: 'Reports', href: '/universal-inventory/reports' },
      { name: 'Standard Reports', href: '/universal-inventory/reports/standard' },
      { name: 'AI Intelligence', href: '/universal-inventory/intelligence' },
      { name: 'AI Copilot', href: '/universal-inventory/intelligence/copilot' },
    ],
  },
  {
    name: 'Omnichannel Billing',
    href: '/omnichannel-billing/analytics/dashboard',
    icon: <Receipt />,
    children: [
      { name: 'Sales Dashboard', href: '/omnichannel-billing/analytics/dashboard' },
      { name: 'Financial Analytics', href: '/omnichannel-billing/analytics/financial' },
      { name: 'Sales Analytics', href: '/omnichannel-billing/analytics/sales' },
      { name: 'Customers', href: '/omnichannel-billing/customers' },
      { name: 'Quotations', href: '/omnichannel-billing/quotations' },
      { name: 'Orders', href: '/omnichannel-billing/orders' },
      { name: 'Order Queue', href: '/omnichannel-billing/order-queue' },
      { name: 'POS', href: '/omnichannel-billing/pos' },
      { name: 'Invoices', href: '/omnichannel-billing/invoices' },
      { name: 'Payments', href: '/omnichannel-billing/payments' },
      { name: 'Receipts', href: '/omnichannel-billing/receipts' },
      { name: 'Outstanding', href: '/omnichannel-billing/outstanding' },
      { name: 'Collections', href: '/omnichannel-billing/collections' },
      { name: 'Fulfillment', href: '/omnichannel-billing/fulfillment' },
      { name: 'Shipping', href: '/omnichannel-billing/shipping' },
      { name: 'Taxes', href: '/omnichannel-billing/taxes' },
      { name: 'Notes', href: '/omnichannel-billing/notes' },
      { name: 'AI Copilot', href: '/omnichannel-billing/ai-copilot' },
    ],
  },
  {
    name: 'AI Copilot & Finance',
    href: '/finance/reports/dashboard',
    icon: <LineChart />,
    children: [
      { name: 'Reports Dashboard', href: '/finance/reports/dashboard' },
      { name: 'Chart of Accounts', href: '/finance/chart-of-accounts' },
      { name: 'General Ledger', href: '/finance/general-ledger' },
      { name: 'Journal Entries', href: '/finance/journal-entries' },
      { name: 'Accounts Payable', href: '/finance/accounts-payable' },
      { name: 'Accounts Receivable', href: '/finance/accounts-receivable' },
      { name: 'Banking', href: '/finance/banking' },
      { name: 'Expenses', href: '/finance/expenses' },
      { name: 'Assets', href: '/finance/assets' },
      { name: 'Budgeting', href: '/finance/budgeting' },
      { name: 'Forecasting', href: '/finance/forecasting' },
      { name: 'Trial Balance', href: '/finance/reports/trial-balance' },
      { name: 'Profit & Loss', href: '/finance/reports/profit-and-loss' },
      { name: 'Balance Sheet', href: '/finance/reports/balance-sheet' },
      { name: 'Cash Flow', href: '/finance/reports/cash-flow' },
      { name: 'CFO Dashboard', href: '/finance/ai-copilot/cfo-dashboard' },
      { name: 'Risk Dashboard', href: '/finance/ai-copilot/risk-dashboard' },
      { name: 'Copilot Chat', href: '/finance/ai-copilot/chat' },
    ],
  },
  {
    name: 'Data Migration Hub',
    href: '/migration',
    icon: <Database />,
    children: [
      { name: 'Overview', href: '/migration' },
      { name: 'Connectors', href: '/migration/connectors' },
      { name: 'Execution', href: '/migration/execution' },
      { name: 'AI Copilot', href: '/migration/ai-copilot' },
    ],
  },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [expanded, setExpanded] = useState<Set<string>>(() => {
    const initial = new Set<string>();
    for (const item of navItems) {
      if (item.children?.some((c) => pathname === c.href || pathname.startsWith(c.href + '/'))) {
        initial.add(item.name);
      }
    }
    return initial;
  });

  const toggle = (name: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(name)) {
        next.delete(name);
      } else {
        next.add(name);
      }
      return next;
    });
  };

  return (
    <aside className={styles.sidebar}>
      <div className={styles.brand}>
        <div className={styles.logoIcon}>AI</div>
        AI-Native ERP
      </div>

      <div className={styles.sectionTitle}>Main Menu</div>
      <nav className={styles.nav}>
        {navItems.map((item) => {
          const hasChildren = !!item.children?.length;
          const isChildActive = item.children?.some(
            (c) => pathname === c.href || pathname.startsWith(c.href + '/')
          );
          const isActive =
            !hasChildren &&
            pathname.startsWith(item.href) &&
            (item.href !== '/dashboard' || pathname === '/dashboard');
          const isOpen = expanded.has(item.name);

          if (!hasChildren) {
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`${styles.navItem} ${isActive ? styles.active : ''}`}
              >
                {item.icon}
                {item.name}
              </Link>
            );
          }

          return (
            <div key={item.name}>
              <button
                type="button"
                onClick={() => toggle(item.name)}
                className={`${styles.navItem} ${styles.navGroupButton} ${isChildActive ? styles.active : ''}`}
                aria-expanded={isOpen}
              >
                {item.icon}
                <span style={{ flex: 1, textAlign: 'left' }}>{item.name}</span>
                <ChevronDown
                  className={styles.chevron}
                  style={{ transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)' }}
                />
              </button>
              {isOpen && (
                <div className={styles.subNav}>
                  {item.children!.map((child) => {
                    const childActive = pathname === child.href || pathname.startsWith(child.href + '/');
                    return (
                      <Link
                        key={child.href}
                        href={child.href}
                        className={`${styles.subNavItem} ${childActive ? styles.active : ''}`}
                      >
                        {child.name}
                      </Link>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </nav>
    </aside>
  );
}
