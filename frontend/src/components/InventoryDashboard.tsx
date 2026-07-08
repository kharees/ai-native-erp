/**
 * components/InventoryDashboard.tsx
 * ==================================
 * Phase 6 — Live inventory dashboard table + form integration.
 *
 * Tenant resolution (updated)
 * ---------------------------
 * Tenant UUID is resolved via `useTenantSession()` — a layered extractor
 * that reads from Supabase session JWT `app_metadata.tenant_id` in production,
 * falls back to `NEXT_PUBLIC_TENANT_ID` in development, and surfaces a typed
 * `AuthState` discriminant for conditional rendering.
 *
 * The `setActiveTenant()` call is now inside `useTenantSession` — no manual
 * Axios seeding is needed here.
 *
 * Other responsibilities
 * ----------------------
 *  2. Calls `useInventoryList()` → paginated catalog table with optimistic inserts.
 *  3. Calls `useCreateInventory()` → wires DynamicInventoryForm to real POST.
 *  4. Live stats strip derived from real API data.
 *  5. Saree-type filter bar + pagination wired to Zustand store actions.
 */

'use client'

import React, { useEffect, useState, useCallback } from 'react'
import {
  Package,
  Plus,
  BarChart3,
  AlertTriangle,
  TrendingUp,
  RefreshCw,
  Search,
  Filter,
  X,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Database,
  Layers,
  Factory,
  ShoppingBag,
} from 'lucide-react'

import DynamicInventoryForm from '@/components/dynamic-inventory-form'
import { useInventoryList, useCreateInventory } from '@/hooks/useInventory'
import { useInventoryStore }                    from '@/store/inventoryStore'
import { useTenantSession }                     from '@/hooks/useTenantSession'
import type {
  CreateInventoryItemPayload,
  InventoryItem,
  InventoryStatusMeta,
  InventoryTableColumn,
} from '@/types/inventory'
import { INVENTORY_STATUS_META } from '@/types/inventory'

import styles from './InventoryDashboard.module.css'

// =============================================================================
// Helpers
// =============================================================================

const TEMPLATE_ICON: Record<string, React.ReactNode> = {
  Manufacturing: <Factory  size={13} />,
  Retail:        <ShoppingBag size={13} />,
  Services:      <Layers   size={13} />,
}

const TEMPLATE_COLOR: Record<string, string> = {
  Manufacturing: '#f59e0b',
  Retail:        '#8b5cf6',
  Services:      '#06b6d4',
}

// STATUS_COLOR is now driven by the exhaustive INVENTORY_STATUS_META map
// imported from @/types/inventory. Adding a new InventoryStatus without
// updating INVENTORY_STATUS_META is a TypeScript compile-time error.

function formatCurrency(value: number, currency: string): string {
  try {
    return new Intl.NumberFormat('en-IN', {
      style:    'currency',
      currency,
      maximumFractionDigits: 2,
    }).format(value)
  } catch {
    return `${currency} ${value.toFixed(2)}`
  }
}

// =============================================================================
// Sub-components
// =============================================================================

function EmptyState({ isFiltered }: { isFiltered: boolean }) {
  return (
    <div className={styles.emptyState}>
      <div className={styles.emptyIcon}>
        <Database size={32} />
      </div>
      <p className={styles.emptyTitle}>
        {isFiltered ? 'No items match your filters' : 'No inventory items yet'}
      </p>
      <p className={styles.emptySub}>
        {isFiltered
          ? 'Try adjusting the saree type or attribute filter above.'
          : 'Create your first item using the form below.'}
      </p>
    </div>
  )
}

function SkeletonRow() {
  return (
    <tr className={styles.skeletonRow}>
      {Array.from({ length: 7 }).map((_, i) => (
        <td key={i}><span className={styles.skeleton} /></td>
      ))}
    </tr>
  )
}

interface InventoryTableProps {
  items:      InventoryItem[]
  isFetching: boolean
  lastCreatedId: string | null
}

function InventoryTable({ items, isFetching, lastCreatedId }: InventoryTableProps) {
  return (
    <div className={styles.tableWrapper}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>SKU</th>
            <th>Name</th>
            <th>Template</th>
            <th>Category</th>
            <th>Unit Price</th>
            <th>Stock</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {isFetching && items.length === 0
            ? Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} />)
            : items.map((item) => (
                <tr
                  key={item.id}
                  className={`${styles.dataRow} ${item.id === lastCreatedId ? styles.newRow : ''}`}
                >
                  <td>
                    <code className={styles.sku}>{item.sku}</code>
                  </td>
                  <td>
                    <span className={styles.itemName}>{item.name}</span>
                    {item.brand && (
                      <span className={styles.itemBrand}>{item.brand}</span>
                    )}
                  </td>
                  <td>
                    <span
                      className={styles.templateBadge}
                      style={{ color: TEMPLATE_COLOR[item.attributes.template] ?? '#9898b8' }}
                    >
                      {TEMPLATE_ICON[item.attributes.template]}
                      {item.attributes.template}
                    </span>
                  </td>
                  <td>
                    <span className={styles.categoryCell}>
                      {item.category ?? <span className={styles.muted}>—</span>}
                    </span>
                  </td>
                  <td>{formatCurrency(item.unit_price, item.currency)}</td>
                  <td>
                    <span
                      className={`${styles.stockBadge} ${
                        item.quantity_on_hand <= item.reorder_level
                          ? styles.stockLow
                          : styles.stockOk
                      }`}
                    >
                      {item.quantity_on_hand}
                      <span className={styles.stockUnit}>{item.unit_of_measure}</span>
                    </span>
                  </td>
                  <td>
                    <span
                      className={styles.statusDot}
                      style={{ background: INVENTORY_STATUS_META[item.status]?.color ?? '#6b7280' }}
                    />
                    <span className={styles.statusText}>
                      {INVENTORY_STATUS_META[item.status]?.label ?? item.status}
                    </span>
                  </td>
                </tr>
              ))}
        </tbody>
      </table>

      {!isFetching && items.length === 0 && <EmptyState isFiltered={false} />}
    </div>
  )
}

// =============================================================================
// Auth gate sub-components
// =============================================================================

function SessionResolving() {
  return (
    <div className={styles.authGate} role="status" aria-live="polite">
      <Loader2 size={22} className={styles.spin} />
      <span>Resolving session…</span>
    </div>
  )
}

function SessionUnauthenticated() {
  return (
    <div className={styles.authGate} role="alert">
      <AlertCircle size={22} style={{ color: '#f59e0b' }} />
      <span>No active tenant session. Sign in to access the inventory ledger.</span>
    </div>
  )
}

// =============================================================================
// Main Dashboard Component
// =============================================================================

const PAGE_SIZE = 20

export default function InventoryDashboard() {
  // ── Tenant session — Supabase JWT extractor (Priority 1)
  //                  — NEXT_PUBLIC_TENANT_ID env override  (Priority 2)
  //                  — null / unauthenticated state        (Priority 3)
  // ─────────────────────────────────────────────────────────────────────────
  const { tenantId, isLoading, authState } = useTenantSession()

  // ── Filter state ─────────────────────────────────────────────────────────
  const [sareeType, setSareeType] = useState('')
  const [attrKey,   setAttrKey]   = useState('')
  const [attrValue, setAttrValue] = useState('')
  const [page,      setPage]      = useState(0)

  // Applied filter (only changes when user clicks "Apply")
  const [appliedFilters, setAppliedFilters] = useState<{
    saree_type?: string
  }>({})

  // ── Data hooks ───────────────────────────────────────────────────────────
  const { items, meta, isFetching, error, clearError, fetchPage } = useInventoryList(
    { ...appliedFilters, limit: PAGE_SIZE, offset: page * PAGE_SIZE },
    tenantId ?? undefined,
  )

  const { mutation: createMutation, isCreating, lastCreated } = useCreateInventory()

  // ── Computed stats ────────────────────────────────────────────────────────
  const totalSKUs  = meta?.total ?? 0
  const lowStock   = items.filter((i) => i.quantity_on_hand <= i.reorder_level).length
  const activeCount = items.filter((i) => i.status === 'active').length
  const draftCount  = items.filter((i) => i.status === 'draft').length

  // ── Handlers ─────────────────────────────────────────────────────────────
  const handleApplyFilters = useCallback(() => {
    setPage(0)
    setAppliedFilters(sareeType ? { saree_type: sareeType } : {})
  }, [sareeType])

  const handleClearFilters = useCallback(() => {
    setSareeType('')
    setAttrKey('')
    setAttrValue('')
    setAppliedFilters({})
    setPage(0)
  }, [])

  const handleFormSubmit = useCallback(
    async (payload: CreateInventoryItemPayload): Promise<void> => {
      await createMutation.mutateAsync(payload)
    },
    [createMutation],
  )

  const handleRefresh = useCallback(() => {
    fetchPage(page * PAGE_SIZE)
  }, [fetchPage, page])

  // ── Toast state ───────────────────────────────────────────────────────────
  const [showSuccess, setShowSuccess] = useState(false)
  useEffect(() => {
    if (lastCreated) {
      setShowSuccess(true)
      const t = setTimeout(() => setShowSuccess(false), 4000)
      return () => clearTimeout(t)
    }
  }, [lastCreated])

  const isFiltered = Boolean(sareeType)
  const totalPages = meta ? Math.ceil(meta.total / PAGE_SIZE) : 0

  // =============================================================================
  // Render — auth-gate first, then the live dashboard
  // =============================================================================

  if (isLoading)                   return <SessionResolving />
  if (authState !== 'authenticated') return <SessionUnauthenticated />

  return (
    <div className={styles.root}>

      {/* ── Toasts ─────────────────────────────────────────────────────── */}
      {showSuccess && (
        <div className={styles.toastSuccess} role="alert" aria-live="polite">
          <CheckCircle2 size={16} />
          Item <strong>{lastCreated?.sku}</strong> created successfully!
          <button onClick={() => setShowSuccess(false)} aria-label="Dismiss">
            <X size={14} />
          </button>
        </div>
      )}
      {error && (
        <div className={styles.toastError} role="alert" aria-live="assertive">
          <AlertCircle size={16} />
          {error.message}
          <button onClick={clearError} aria-label="Dismiss">
            <X size={14} />
          </button>
        </div>
      )}

      {/* ── Live Stats Strip ────────────────────────────────────────────── */}
      <section aria-label="Live inventory statistics" className={styles.statsStrip}>
        {[
          { label: 'Total SKUs',   value: totalSKUs,   sub: 'Across all categories', icon: Package,       color: '#8b5cf6' },
          { label: 'Low Stock',    value: lowStock,     sub: 'Below reorder level',  icon: AlertTriangle, color: '#f59e0b' },
          { label: 'Active Items', value: activeCount,  sub: 'Status: active',        icon: TrendingUp,    color: '#10b981' },
          { label: 'Draft Items',  value: draftCount,   sub: 'Pending review',        icon: BarChart3,     color: '#06b6d4' },
        ].map(({ label, value, sub, icon: Icon, color }) => (
          <div key={label} className={styles.statCard}>
            <div className={styles.statIconWrap} style={{ color }}>
              <Icon size={16} />
            </div>
            <div>
              <span className={styles.statLabel}>{label}</span>
              <span className={styles.statValue}>
                {isFetching && value === 0
                  ? <span className={styles.skeleton} style={{ width: 40, height: 22, display: 'inline-block', borderRadius: 4 }} />
                  : value}
              </span>
              <span className={styles.statSub}>{sub}</span>
            </div>
          </div>
        ))}
      </section>

      {/* ── Catalog Table ────────────────────────────────────────────────── */}
      <section aria-labelledby="catalog-heading" className={styles.tableSection}>

        {/* Header row */}
        <div className={styles.tableHeader}>
          <div>
            <h2 id="catalog-heading" className={styles.sectionTitle}>
              Live Catalog
              {isFetching && (
                <span className={styles.fetchingBadge}>
                  <Loader2 size={12} className={styles.spin} /> Syncing…
                </span>
              )}
            </h2>
            {meta && (
              <p className={styles.sectionSub}>
                Showing {items.length} of {meta.total} items
                {isFiltered && ` — filtered by "${sareeType}"`}
              </p>
            )}
          </div>

          <div className={styles.tableActions}>
            {/* Saree-type filter */}
            <div className={styles.searchWrap}>
              <Search size={14} className={styles.searchIcon} />
              <input
                className={styles.searchInput}
                type="text"
                placeholder="Filter by saree type…"
                value={sareeType}
                onChange={(e) => setSareeType(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleApplyFilters()}
                aria-label="Filter by saree type"
              />
            </div>

            <button
              className={styles.btnSecondary}
              onClick={handleApplyFilters}
              aria-label="Apply filters"
            >
              <Filter size={13} /> Apply
            </button>

            {isFiltered && (
              <button
                className={styles.btnGhost}
                onClick={handleClearFilters}
                aria-label="Clear filters"
              >
                <X size={13} /> Clear
              </button>
            )}

            <button
              className={styles.btnGhost}
              onClick={handleRefresh}
              disabled={isFetching}
              aria-label="Refresh catalog"
            >
              <RefreshCw size={13} className={isFetching ? styles.spin : undefined} />
            </button>
          </div>
        </div>

        {/* Table */}
        <InventoryTable
          items={items}
          isFetching={isFetching}
          lastCreatedId={lastCreated?.id ?? null}
        />

        {/* Pagination */}
        {totalPages > 1 && (
          <div className={styles.pagination}>
            <button
              className={styles.btnGhost}
              onClick={() => { setPage((p) => Math.max(0, p - 1)); fetchPage((page - 1) * PAGE_SIZE) }}
              disabled={page === 0}
              aria-label="Previous page"
            >
              <ChevronLeft size={14} />
            </button>
            <span className={styles.pageInfo}>
              Page {page + 1} of {totalPages}
            </span>
            <button
              className={styles.btnGhost}
              onClick={() => { setPage((p) => p + 1); fetchPage((page + 1) * PAGE_SIZE) }}
              disabled={!meta?.has_more}
              aria-label="Next page"
            >
              <ChevronRight size={14} />
            </button>
          </div>
        )}
      </section>

      {/* ── Create Form ──────────────────────────────────────────────────── */}
      <section aria-labelledby="create-heading" className={styles.formSection}>
        <div className={styles.formHeader}>
          <div>
            <h2 id="create-heading" className={styles.sectionTitle}>
              <span className={styles.formTitleIcon} aria-hidden>
                <Plus size={15} />
              </span>
              New Inventory Item
            </h2>
            <p className={styles.sectionSub}>
              Select an industry template — attribute fields adapt dynamically.
              Payload is posted directly to{' '}
              <code className={styles.inlineCode}>POST /api/v1/inventory/saree/</code>.
            </p>
          </div>

          {isCreating && (
            <div className={styles.creatingBadge}>
              <Loader2 size={13} className={styles.spin} /> Saving to ledger…
            </div>
          )}
        </div>

        <DynamicInventoryForm onSubmit={handleFormSubmit} />
      </section>

    </div>
  )
}
