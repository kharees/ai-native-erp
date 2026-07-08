/**
 * app/inventory/page.tsx
 * =======================
 * Phase 6 — Inventory Management page (State-wired version).
 *
 * Architecture
 * ------------
 *  • This file remains a React Server Component (no 'use client') for fast
 *    initial paint and SEO.
 *  • The heavy lifting is delegated to <InventoryDashboard />, which is a
 *    Client Component that:
 *      1. Seeds the Axios singleton with the active tenant UUID.
 *      2. Calls useInventoryList() to load and bind the live catalog into
 *         the dashboard table (replaces '—' placeholder stats).
 *      3. Passes useCreateInventory().mutateAsync to DynamicInventoryForm's
 *         onSubmit — replacing the old console-log stub with a real POST.
 *
 * Route:  /inventory
 * Dev:    http://localhost:3000/inventory
 */

import type { Metadata } from 'next'

import InventoryDashboard from '@/components/InventoryDashboard'
import styles from './page.module.css'

// =============================================================================
// SEO
// =============================================================================

export const metadata: Metadata = {
  title: 'Inventory Management | AI-Native ERP',
  description:
    'Create and manage multi-tenant inventory items across Manufacturing, Retail, and Services templates with dynamic JSONB attribute matrices.',
  robots: { index: false, follow: false },
}

// =============================================================================
// Page Component
// =============================================================================

export default function InventoryPage() {
  return (
    <main className={styles.root}>
      <div className={styles.inner}>

        {/* ── Page Header ──────────────────────────────────────────── */}
        <header className={styles.header}>
          <div className={styles.headerLeft}>
            <nav aria-label="breadcrumb" className={styles.breadcrumb}>
              <span>ERP</span>
              <span className={styles.breadcrumbSep}>›</span>
              <span className={styles.breadcrumbCurrent}>Inventory</span>
            </nav>

            <h1 className={styles.pageTitle}>Inventory Management</h1>
            <p className={styles.pageSubtitle}>
              Live multi-tenant catalog — powered by FastAPI, Supabase, and
              async SQLAlchemy 2.0. Data streams in from{' '}
              <code style={{ fontSize: 12, opacity: 0.7 }}>
                GET /api/v1/inventory/saree/
              </code>.
            </p>

            <div className={styles.headerBadge}>
              <span className={styles.dot} aria-hidden />
              Phase 6 · State Wired · Live API
            </div>
          </div>
        </header>

        {/* ── Divider ───────────────────────────────────────────────── */}
        <div className={styles.divider} />

        {/*
          InventoryDashboard owns:
            • Live stats strip (derived from real API data)
            • Catalog table with pagination + filters
            • DynamicInventoryForm wired to the real POST endpoint
            • Toast notifications for success / error
        */}
        <InventoryDashboard />

      </div>
    </main>
  )
}
