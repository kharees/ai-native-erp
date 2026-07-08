/**
 * store/inventoryStore.ts
 * ========================
 * Phase 6 — Zustand state management store for the Inventory module.
 *
 * Architecture
 * ------------
 *  • Single Zustand slice that owns all inventory UI state:
 *      - The fetched items array (the data source for the dashboard table).
 *      - Pagination metadata (total, limit, offset, has_more).
 *      - Per-operation loading flags (isFetching, isCreating).
 *      - A typed error slot for the last API failure.
 *      - Active filter state (saree_type, jsonb key/value filters).
 *  • Async action functions (`loadInventory`, `submitNewItem`,
 *    `applyAttributeFilter`) call the service layer and write results
 *    directly into the store — no thunks or middleware required.
 *  • React Query hooks in `hooks/useInventory.ts` wrap these actions
 *    for automatic cache invalidation, retry, and background refresh.
 *    The Zustand store is the single source of truth for the *rendered*
 *    dataset; React Query drives the *fetching lifecycle*.
 *
 * Usage
 * -----
 *  // Read state in a component:
 *  const items = useInventoryStore((s) => s.items)
 *  const isFetching = useInventoryStore((s) => s.isFetching)
 *
 *  // Dispatch an action:
 *  const loadInventory = useInventoryStore((s) => s.loadInventory)
 *  await loadInventory({ limit: 20 })
 */

import { create } from 'zustand'
import { devtools } from 'zustand/middleware'

import {
  fetchInventory,
  createInventoryItem,
  filterByJsonbAttribute,
  type FetchInventoryParams,
  type FilterByAttributeParams,
  type PaginationMeta,
} from '@/services/inventoryService'
import type { InventoryItem, CreateInventoryItemPayload } from '@/types/inventory'
import type { ApiError } from '@/lib/apiClient'

// =============================================================================
// 1.  State shape
// =============================================================================

export interface InventoryState {
  // ── Data ──────────────────────────────────────────────────────────────────
  /** Current page of inventory items rendered in the dashboard table. */
  items:     InventoryItem[]
  /** Pagination metadata from the last successful list fetch. */
  meta:      PaginationMeta | null
  /** The item just created (used to highlight the new row / show success). */
  lastCreated: InventoryItem | null

  // ── Loading flags ─────────────────────────────────────────────────────────
  /** True while a list-fetch or attribute-filter request is in flight. */
  isFetching:  boolean
  /** True while a POST /inventory create request is in flight. */
  isCreating:  boolean

  // ── Error slot ────────────────────────────────────────────────────────────
  /** Typed error from the last failed API call, or null if last call succeeded. */
  error: ApiError | null

  // ── Active filter state ───────────────────────────────────────────────────
  /** Current query params applied to the list (preserved for re-fetch). */
  activeFilters: FetchInventoryParams

  // ── Actions ───────────────────────────────────────────────────────────────
  /**
   * Fetch (or re-fetch) the tenant's saree inventory catalog.
   * Merges supplied params with the existing `activeFilters`.
   * Updates `items`, `meta`, `isFetching`, and `error`.
   */
  loadInventory: (params?: FetchInventoryParams) => Promise<void>

  /**
   * Submit a new inventory item payload from the Phase 3 form.
   * On success: prepends the new item to `items`, sets `lastCreated`.
   * On failure: writes the ApiError to `error`.
   */
  submitNewItem: (payload: CreateInventoryItemPayload) => Promise<InventoryItem>

  /**
   * Apply a JSONB attribute key/value filter against the tenant's catalog.
   * Replaces `items` and `meta` with the filtered result set.
   */
  applyAttributeFilter: (params: FilterByAttributeParams) => Promise<void>

  /** Reset `error` to null (called after the user dismisses an error toast). */
  clearError: () => void

  /** Reset items + meta + filters to initial state (e.g. on page unmount). */
  reset: () => void
}

// =============================================================================
// 2.  Default pagination meta sentinel
// =============================================================================

const DEFAULT_META: PaginationMeta = {
  total:    0,
  limit:    50,
  offset:   0,
  has_more: false,
}

// =============================================================================
// 3.  Store
// =============================================================================

export const useInventoryStore = create<InventoryState>()(
  devtools(
    (set, get) => ({
      // ── Initial state ────────────────────────────────────────────────────
      items:        [],
      meta:         null,
      lastCreated:  null,
      isFetching:   false,
      isCreating:   false,
      error:        null,
      activeFilters: {},

      // ── loadInventory ────────────────────────────────────────────────────
      loadInventory: async (params: FetchInventoryParams = {}) => {
        const merged: FetchInventoryParams = {
          ...get().activeFilters,
          ...params,
        }

        set(
          { isFetching: true, error: null, activeFilters: merged },
          false,
          'inventory/loadInventory/pending',
        )

        try {
          const { items, meta } = await fetchInventory(merged)
          set(
            { items, meta, isFetching: false },
            false,
            'inventory/loadInventory/fulfilled',
          )
        } catch (err) {
          set(
            { isFetching: false, error: err as ApiError },
            false,
            'inventory/loadInventory/rejected',
          )
        }
      },

      // ── submitNewItem ─────────────────────────────────────────────────────
      submitNewItem: async (payload: CreateInventoryItemPayload) => {
        set(
          { isCreating: true, error: null },
          false,
          'inventory/submitNewItem/pending',
        )

        try {
          const newItem = await createInventoryItem(payload)

          // Prepend the new item to the local list so the table updates
          // instantly without waiting for a re-fetch.
          const currentItems = get().items
          const currentMeta  = get().meta ?? DEFAULT_META

          set(
            {
              isCreating:  false,
              lastCreated: newItem,
              items:       [newItem, ...currentItems],
              meta: {
                ...currentMeta,
                total: currentMeta.total + 1,
              },
            },
            false,
            'inventory/submitNewItem/fulfilled',
          )

          return newItem
        } catch (err) {
          set(
            { isCreating: false, error: err as ApiError },
            false,
            'inventory/submitNewItem/rejected',
          )
          throw err   // re-throw so the form's mutation.onError handler fires
        }
      },

      // ── applyAttributeFilter ──────────────────────────────────────────────
      applyAttributeFilter: async (params: FilterByAttributeParams) => {
        set(
          { isFetching: true, error: null },
          false,
          'inventory/applyAttributeFilter/pending',
        )

        try {
          const { items, meta } = await filterByJsonbAttribute(params)
          set(
            { items, meta, isFetching: false },
            false,
            'inventory/applyAttributeFilter/fulfilled',
          )
        } catch (err) {
          set(
            { isFetching: false, error: err as ApiError },
            false,
            'inventory/applyAttributeFilter/rejected',
          )
        }
      },

      // ── clearError ────────────────────────────────────────────────────────
      clearError: () => set({ error: null }, false, 'inventory/clearError'),

      // ── reset ─────────────────────────────────────────────────────────────
      reset: () =>
        set(
          {
            items:         [],
            meta:          null,
            lastCreated:   null,
            isFetching:    false,
            isCreating:    false,
            error:         null,
            activeFilters: {},
          },
          false,
          'inventory/reset',
        ),
    }),
    { name: 'InventoryStore' },
  ),
)
