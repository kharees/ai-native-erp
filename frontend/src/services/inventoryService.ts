/**
 * services/inventoryService.ts
 * =============================
 * Phase 6 — Async client service layer for the Inventory module.
 *
 * Maps 1-to-1 with the FastAPI backend endpoints:
 *
 *   GET  /api/v1/inventory/saree/                     → fetchInventory()
 *   POST /api/v1/inventory/saree/                     → createInventoryItem()
 *   GET  /api/v1/inventory/saree/filter-attributes/   → filterByJsonbAttribute()
 *
 * Security
 * --------
 *   The `X-Tenant-ID` header is injected automatically by the Axios request
 *   interceptor in `lib/apiClient.ts` — no manual header management needed
 *   in this file.  Call `setActiveTenant(uuid)` once after session resolves.
 *
 * Typing
 * ------
 *   All request / response shapes are imported from `@/types/inventory` —
 *   the same types already used by the Phase 3 form component, so end-to-end
 *   type safety is guaranteed from the Zod-validated form submission all the
 *   way to the API response parsed by the dashboard table.
 */

import apiClient from '@/lib/apiClient'
import type {
  InventoryItem,
  CreateInventoryItemPayload,
} from '@/types/inventory'

// =============================================================================
// 1.  Response envelope types (mirror backend Pydantic schemas)
// =============================================================================

/** PaginationMeta block included in every list response. */
export interface PaginationMeta {
  total:    number
  limit:    number
  offset:   number
  has_more: boolean
}

/** Paginated list response for all GET /inventory/* list endpoints. */
export interface InventoryListResponse {
  items: InventoryItem[]
  meta:  PaginationMeta
}

// =============================================================================
// 2.  Query param shapes (type-safe call-site arguments)
// =============================================================================

/** Parameters accepted by `fetchInventory()`. */
export interface FetchInventoryParams {
  /**
   * Optional case-insensitive saree-type filter (ILIKE against `category`).
   * e.g. "kanjivaram" matches "Kanjivaram", "KANJIVARAM", etc.
   */
  saree_type?: string
  /** Page size. Range 1–200. Default: 50. */
  limit?: number
  /** Zero-based page offset. Default: 0. */
  offset?: number
}

/** Parameters accepted by `filterByJsonbAttribute()`. */
export interface FilterByAttributeParams {
  /** Top-level JSONB key inside `attributes` to filter on (e.g. "template", "color"). */
  key:    string
  /** Exact string value to match (via Postgres `->>`). Case-sensitive. */
  value:  string
  /** Page size. Range 1–200. Default: 50. */
  limit?: number
  /** Zero-based page offset. Default: 0. */
  offset?: number
}

// =============================================================================
// 3.  API base path constant
// =============================================================================

/** Shared prefix for all inventory endpoints. */
const INVENTORY_BASE = '/api/v1/inventory/saree'

// =============================================================================
// 4.  fetchInventory()
// =============================================================================

/**
 * Stream the authenticated tenant's paginated saree inventory catalog.
 *
 * Maps to:  `GET /api/v1/inventory/saree/`
 *
 * The `X-Tenant-ID` header is injected automatically — no header management
 * required at the call site. Set the active tenant once via
 * `setActiveTenant(uuid)` from `@/lib/apiClient`.
 *
 * @param params - Optional pagination and saree-type filter parameters.
 * @returns      - Paginated list of inventory items with metadata.
 *
 * @throws {ApiError} On 400 / 401 / 403 / 500 HTTP errors (typed, normalised).
 *
 * @example
 * const { items, meta } = await fetchInventory({ saree_type: 'kanjivaram', limit: 20 })
 */
export async function fetchInventory(
  params: FetchInventoryParams = {},
): Promise<InventoryListResponse> {
  const { saree_type, limit = 50, offset = 0 } = params

  // Build query-string object; omit undefined keys so Axios doesn't
  // serialise them as "saree_type=undefined".
  const query: Record<string, string | number> = { limit, offset }
  if (saree_type) query.saree_type = saree_type

  const response = await apiClient.get<InventoryListResponse>(
    `${INVENTORY_BASE}/`,
    { params: query },
  )

  return response.data
}

// =============================================================================
// 5.  createInventoryItem()
// =============================================================================

/**
 * Ingest a new saree inventory node into the multi-tenant handloom ledger.
 *
 * Maps to:  `POST /api/v1/inventory/saree/`
 *
 * The payload originates from `DynamicInventoryForm` after Zod validation
 * — the `attributes` field is the discriminated union (Manufacturing | Retail
 * | Services) formed in the form's submit handler.
 *
 * Duplicate SKU detection is performed server-side; the backend returns
 * HTTP 400 if a node with the same SKU already exists for this tenant.
 *
 * @param payload - Validated `CreateInventoryItemPayload` from the form.
 * @returns        - The persisted `InventoryItem` with server-generated
 *                   `id`, `tenant_id`, `created_at`, and `updated_at`.
 *
 * @throws {ApiError}  400 — Duplicate SKU for this tenant.
 * @throws {ApiError}  401 — Missing X-Tenant-ID (middleware guard).
 * @throws {ApiError}  403 — Invalid / inactive tenant UUID.
 * @throws {ApiError}  422 — Payload failed Pydantic validation.
 *
 * @example
 * const newItem = await createInventoryItem({
 *   sku: 'KNJ-RED-001', name: 'Kanjivaram Red Silk', ...attrs
 * })
 */
export async function createInventoryItem(
  payload: CreateInventoryItemPayload,
): Promise<InventoryItem> {
  const response = await apiClient.post<InventoryItem>(
    `${INVENTORY_BASE}/`,
    payload,
  )
  // FastAPI returns 201 Created; Axios resolves on 2xx
  return response.data
}

// =============================================================================
// 6.  filterByJsonbAttribute()
// =============================================================================

/**
 * Advanced JSONB attribute query against the tenant's saree catalog.
 *
 * Maps to:  `GET /api/v1/inventory/saree/filter-attributes/`
 *
 * Executes a Postgres `attributes->>'key' = 'value'` predicate via
 * SQLAlchemy's `astext()` operator on the server, leveraging the GIN
 * index on the JSONB column for high-performance queries.
 *
 * @param params - JSONB key + value filter with optional pagination.
 * @returns      - Paginated list of matching inventory items.
 *
 * @example
 * // Filter by industry template
 * const result = await filterByJsonbAttribute({ key: 'template', value: 'Retail' })
 *
 * // Filter by quality grade
 * const result = await filterByJsonbAttribute({ key: 'quality_grade', value: 'A' })
 */
export async function filterByJsonbAttribute(
  params: FilterByAttributeParams,
): Promise<InventoryListResponse> {
  const { key, value, limit = 50, offset = 0 } = params

  const response = await apiClient.get<InventoryListResponse>(
    `${INVENTORY_BASE}/filter-attributes/`,
    { params: { key, value, limit, offset } },
  )

  return response.data
}

// =============================================================================
// 7.  Convenience re-export
// =============================================================================

/** All exported inventory service functions in a namespace object. */
export const inventoryService = {
  fetchInventory,
  createInventoryItem,
  filterByJsonbAttribute,
} as const
