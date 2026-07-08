/**
 * hooks/useInventory.ts
 * ======================
 * Phase 6 — React Query hooks for inventory data fetching + mutation.
 *
 * These hooks wrap the Zustand store actions with TanStack Query v5 so
 * the component layer gets:
 *  • Automatic background refetch (staleTime, refetchOnWindowFocus).
 *  • Retry logic on transient network errors (3 retries, exponential back-off).
 *  • Deduplication — multiple components mounting simultaneously share one
 *    in-flight request.
 *  • Optimistic mutation handling + cache invalidation on create success.
 *
 * Architecture
 * ------------
 *  ┌──────────────────────┐
 *  │  React Component     │
 *  │  useInventoryList()  │  ← read items / loading / error
 *  │  useCreateInventory()│  ← fire mutation, track isCreating
 *  └──────┬───────────────┘
 *         │  TanStack Query cache
 *  ┌──────▼───────────────┐
 *  │  Zustand Store       │  ← owns rendered dataset (items[])
 *  └──────┬───────────────┘
 *         │
 *  ┌──────▼───────────────┐
 *  │  inventoryService.ts │  ← Axios calls → FastAPI backend
 *  └──────────────────────┘
 *
 * Query Keys
 * ----------
 *  ['inventory', 'list', params]  — list queries (invalidated on create)
 *  ['inventory', 'filter', params] — attribute-filter queries
 */

'use client'

import { useCallback } from 'react'
import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryResult,
  type UseMutationResult,
} from '@tanstack/react-query'

import { useInventoryStore, type InventoryState }  from '@/store/inventoryStore'
import type {
  FetchInventoryParams,
  FilterByAttributeParams,
  InventoryListResponse,
} from '@/services/inventoryService'
import type { InventoryItem, CreateInventoryItemPayload } from '@/types/inventory'
import type { ApiError } from '@/lib/apiClient'

// =============================================================================
// 1.  Query key factory
// =============================================================================

export const inventoryKeys = {
  all:    ['inventory'] as const,
  lists:  () => [...inventoryKeys.all, 'list'] as const,
  list:   (params: FetchInventoryParams) => [...inventoryKeys.lists(), params] as const,
  filter: (params: FilterByAttributeParams) =>
    [...inventoryKeys.all, 'filter', params] as const,
}

// =============================================================================
// 2.  useInventoryList()
// =============================================================================

/**
 * Hook that fetches and subscribes to the tenant's saree inventory catalog.
 *
 * On first mount it triggers a GET request via the Zustand `loadInventory`
 * action and writes the result into the store.  Subsequent renders read from
 * the store — no prop-drilling or context required.
 *
 * @param params - Optional pagination / saree_type filter params.
 * @param tenantId - Active tenant UUID (required; enables the query when set).
 *
 * @returns TanStack Query result + convenience accessors into the Zustand store.
 *
 * @example
 * const { items, isFetching, error } = useInventoryList({ limit: 20 }, tenantId)
 */
export function useInventoryList(
  params: FetchInventoryParams = {},
  tenantId?: string,
): {
  // TanStack Query fields
  queryResult: UseQueryResult<InventoryListResponse, ApiError>
  // Zustand store values (always up-to-date including optimistic updates)
  items:      InventoryItem[]
  meta:       InventoryState['meta']
  isFetching: boolean
  error:      ApiError | null
  clearError: () => void
  // Pagination helpers
  fetchPage:  (offset: number) => void
} {
  const queryClient = useQueryClient()

  const {
    items,
    meta,
    isFetching,
    error,
    loadInventory,
    clearError,
  } = useInventoryStore()

  const queryResult = useQuery<InventoryListResponse, ApiError>({
    queryKey:  inventoryKeys.list(params),
    queryFn:   async () => {
      await loadInventory(params)
      // Return the store's current state as the query data so React Query
      // also caches it — allows DevTools inspection and SSR hydration.
      const state = useInventoryStore.getState()
      return { items: state.items, meta: state.meta ?? { total: 0, limit: 50, offset: 0, has_more: false } }
    },
    enabled:   Boolean(tenantId),   // don't fire until tenant is known
    staleTime: 30_000,              // 30 s — background refetch window
    retry:     3,
    retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 10_000),
  })

  /** Fetch a specific page offset without changing other filters. */
  const fetchPage = useCallback(
    (offset: number) => {
      queryClient.invalidateQueries({ queryKey: inventoryKeys.lists() })
      loadInventory({ ...params, offset })
    },
    [loadInventory, params, queryClient],
  )

  return { queryResult, items, meta, isFetching, error, clearError, fetchPage }
}

// =============================================================================
// 3.  useCreateInventory()
// =============================================================================

/**
 * Mutation hook for creating a new inventory item from the Phase 3 form.
 *
 * On success:
 *  • The new item is prepended to the Zustand `items` array immediately
 *    (optimistic-style update via the store action).
 *  • All 'inventory/list' queries are invalidated, triggering a background
 *    refetch so pagination totals are accurate.
 *
 * On error:
 *  • The typed `ApiError` is stored in both the mutation result and the
 *    Zustand store for display in error toasts / banners.
 *
 * @returns TanStack mutation result + convenience wrappers.
 *
 * @example
 * const { mutateAsync, isLoading, error } = useCreateInventory()
 * const newItem = await mutateAsync(formPayload)
 */
export function useCreateInventory(): {
  mutation:    UseMutationResult<InventoryItem, ApiError, CreateInventoryItemPayload>
  isCreating:  boolean
  lastCreated: InventoryItem | null
} {
  const queryClient = useQueryClient()

  const { submitNewItem, isCreating, lastCreated } = useInventoryStore()

  const mutation = useMutation<InventoryItem, ApiError, CreateInventoryItemPayload>({
    mutationFn: (payload) => submitNewItem(payload),

    onSuccess: () => {
      // Invalidate all list queries so next render shows the updated total
      queryClient.invalidateQueries({ queryKey: inventoryKeys.lists() })
    },

    onError: (_error) => {
      // Error is already in the Zustand store via submitNewItem's catch block.
      // Components read it via useInventoryStore((s) => s.error).
    },
  })

  return { mutation, isCreating, lastCreated }
}

// =============================================================================
// 4.  useAttributeFilter()
// =============================================================================

/**
 * Hook for advanced JSONB attribute filtering.
 *
 * Fires a GET /filter-attributes/ request when `enabled` is true and both
 * `key` and `value` are non-empty.  Results replace the Zustand items array.
 *
 * @param params  - JSONB key/value filter + pagination.
 * @param enabled - Set to false to suppress the query (e.g. when filter UI is hidden).
 *
 * @example
 * const { items, isFetching } = useAttributeFilter(
 *   { key: 'template', value: 'Retail', limit: 20 },
 *   isFilterActive,
 * )
 */
export function useAttributeFilter(
  params: FilterByAttributeParams,
  enabled: boolean,
): {
  items:      InventoryItem[]
  isFetching: boolean
  error:      ApiError | null
} {
  const { items, isFetching, error, applyAttributeFilter } = useInventoryStore()

  useQuery<void, ApiError>({
    queryKey:  inventoryKeys.filter(params),
    queryFn:   () => applyAttributeFilter(params),
    enabled:   enabled && Boolean(params.key) && Boolean(params.value),
    staleTime: 30_000,
    retry:     2,
  })

  return { items, isFetching, error }
}
