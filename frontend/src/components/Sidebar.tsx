'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import styles from './Sidebar.module.css';
import { 
  LayoutDashboard, 
  Users, 
  PackageSearch, 
  Receipt, 
  LineChart, 
  Database 
} from 'lucide-react';

export default function Sidebar() {
  const pathname = usePathname();

  const navItems = [
    { name: 'Dashboard', href: '/dashboard', icon: <LayoutDashboard /> },
    { name: 'Master Foundation', href: '/users', icon: <Users /> },
    { name: 'Universal Inventory', href: '/universal-inventory', icon: <PackageSearch /> },
    { name: 'Omnichannel Billing', href: '/omnichannel-billing/analytics/dashboard', icon: <Receipt /> },
    { name: 'AI Copilot & Finance', href: '/finance/reports/dashboard', icon: <LineChart /> },
    { name: 'Data Migration Hub', href: '/migration', icon: <Database /> },
  ];

  return (
    <aside className={styles.sidebar}>
      <div className={styles.brand}>
        <div className={styles.logoIcon}>AI</div>
        AI-Native ERP
      </div>
      
      <div className={styles.sectionTitle}>Main Menu</div>
      <nav className={styles.nav}>
        {navItems.map((item) => {
          const isActive = pathname.startsWith(item.href) && (item.href !== '/dashboard' || pathname === '/dashboard');
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
        })}
      </nav>
    </aside>
  );
}
