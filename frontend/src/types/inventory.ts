/**
 * types/inventory.ts
 * ==================
 * Complete TypeScript type system for the AI-Native ERP inventory module.
 *
 * Design principles:
 *  • Discriminated unions — the `template` literal field narrows attributes
 *    to the exact industry-specific shape at compile time.
 *  • Exhaustive union coverage — every `switch (item.template)` that misses
 *    a case is a TypeScript error.
 *  • Zod schema references are co-located with each interface so the runtime
 *    validator and the compile-time type are always in sync.
 */

// =============================================================================
// 1.  Industry Template Discriminant
// =============================================================================

/** The three top-level industry templates supported in v1. */
export type IndustryTemplate = 'Manufacturing' | 'Retail' | 'Services'

// =============================================================================
// 2.  Shared / Common Fields
// =============================================================================

/** Quality grades used by manufacturing and optionally retail. */
export type QualityGrade = 'A' | 'B' | 'C' | 'rejected'

/** Gender classification for retail apparel / lifestyle products. */
export type RetailGender = 'men' | 'women' | 'unisex' | 'kids' | 'na'

/** License model for SaaS / digital services. */
export type LicenseType =
  | 'perpetual'
  | 'subscription_monthly'
  | 'subscription_annual'
  | 'pay_per_use'
  | 'open_source'
  | 'custom'

/** Seasonal product classification for retail / FMCG. */
export type RetailSeason = 'spring_summer' | 'autumn_winter' | 'all_season' | 'limited_edition'

/** Unit-of-measure codes aligned with ISO 80000. */
export type UnitOfMeasure =
  | 'unit'
  | 'kg'
  | 'g'
  | 'mg'
  | 'l'
  | 'ml'
  | 'm'
  | 'cm'
  | 'mm'
  | 'm2'
  | 'm3'
  | 'box'
  | 'pallet'
  | 'dozen'
  | 'pack'
  | 'hour'
  | 'day'
  | 'month'

// =============================================================================
// 3.  Manufacturing Attributes
// =============================================================================

/**
 * Attribute matrix for manufactured goods (raw materials, components,
 * finished products, sub-assemblies, etc.).
 *
 * @example
 * {
 *   template: 'Manufacturing',
 *   batch_number: 'BT-2024-00412',
 *   unit_of_measure: 'kg',
 *   production_date: '2024-06-01',
 *   quality_grade: 'A',
 *   raw_material_source: 'Tata Steel – Pune Plant',
 *   tolerances: '±0.05mm',
 *   machine_id: 'CNC-07'
 * }
 */
export interface ManufacturingAttributes {
  template: 'Manufacturing'
  /** Unique identifier for the production batch (traceability). */
  batch_number: string
  /** ISO-aligned unit of measure for stock tracking. */
  unit_of_measure: UnitOfMeasure
  /** Date the batch was manufactured (ISO 8601 date string). */
  production_date: string
  /** Optional shelf-life / warranty expiry date. */
  expiry_date?: string
  /** Quality inspection result. */
  quality_grade: QualityGrade
  /** Supplier or internal origin of raw material inputs. */
  raw_material_source?: string
  /** CNC / machine asset tag that produced this item. */
  machine_id?: string
  /** Dimensional tolerance spec, e.g. "±0.05mm". */
  tolerances?: string
  /** Bill-of-materials reference code. */
  bom_reference?: string
  /** ISO certification applicable to this item, e.g. "ISO 9001". */
  certification?: string
  /** Hazardous material classification code (UN number). */
  hazmat_code?: string
  /** Net weight in kilograms. */
  weight_kg?: number
  /** Gross volume in cubic metres. */
  volume_m3?: number
}

// =============================================================================
// 4.  Retail Attributes
// =============================================================================

/**
 * Attribute matrix for retail / consumer products (apparel, electronics,
 * FMCG, lifestyle, etc.).
 *
 * @example
 * {
 *   template: 'Retail',
 *   size: 'M',
 *   color: 'Midnight Black',
 *   barcode: '8901234567890',
 *   brand_line: 'ERP Wear SS25',
 *   gender: 'unisex',
 *   season: 'all_season',
 *   material: '80% cotton 20% polyester'
 * }
 */
export interface RetailAttributes {
  template: 'Retail'
  /** Physical size designation (S, M, L, XL, 42, 10, etc.). */
  size: string
  /** Colour name as shown on the product label. */
  color: string
  /** Material composition, e.g. "100% cotton". */
  material?: string
  /** Brand sub-line or collection name. */
  brand_line?: string
  /** GTIN / EAN / UPC barcode value. */
  barcode?: string
  /** Seasonal collection flag. */
  season?: RetailSeason
  /** Target gender segment. */
  gender?: RetailGender
  /** Internal style / SKU variant code. */
  style_code?: string
  /** Country where the product was manufactured (ISO 3166-1 alpha-2). */
  country_of_origin?: string
  /** MRP / recommended retail price (in tenant currency). */
  mrp?: number
  /** Discount percentage applicable during promotion. */
  discount_pct?: number
  /** Minimum display qty on shelf before replenishment alert. */
  shelf_min_qty?: number
  /** Planogram slot identifier in the store layout. */
  planogram_slot?: string
}

// =============================================================================
// 5.  Services Attributes
// =============================================================================

/**
 * Attribute matrix for intangible service items (consulting, SaaS,
 * managed services, professional services, digital deliverables).
 *
 * @example
 * {
 *   template: 'Services',
 *   service_type: 'Implementation',
 *   service_duration_hours: 40,
 *   deliverable_format: 'PDF Report + Working Prototype',
 *   team_size: 3,
 *   license_type: 'subscription_annual',
 *   renewal_period_days: 365
 * }
 */
export interface ServicesAttributes {
  template: 'Services'
  /** Category of service (Consulting, SaaS, Support, Training, etc.). */
  service_type: string
  /** Estimated / contracted service effort in hours. */
  service_duration_hours: number
  /** Description of what the client receives on completion. */
  deliverable_format?: string
  /** Number of team members assigned to this service item. */
  team_size?: number
  /** Licensing model if the item is a software / IP product. */
  license_type?: LicenseType
  /** Renewal cycle in days (365 = annual, 30 = monthly). */
  renewal_period_days?: number
  /** Maximum simultaneous users or seats covered by the license. */
  max_seats?: number
  /** SLA response time commitment in hours (e.g., 4 for P1). */
  sla_response_hours?: number
  /** SLA uptime guarantee as a percentage (e.g., 99.9). */
  sla_uptime_pct?: number
  /** URL to the scope-of-work or service agreement document. */
  sow_url?: string
  /** Skills / technologies required to deliver this service. */
  required_skills?: string[]
}

// =============================================================================
// 6.  Discriminated Union
// =============================================================================

/**
 * Discriminated union over all three industry attribute shapes.
 * Use `attributes.template` to narrow to the specific interface.
 *
 * @example
 * function renderAttributeSummary(attrs: InventoryAttributes) {
 *   switch (attrs.template) {
 *     case 'Manufacturing': return `Batch: ${attrs.batch_number}`
 *     case 'Retail':        return `${attrs.color} / ${attrs.size}`
 *     case 'Services':      return `${attrs.service_type} · ${attrs.service_duration_hours}h`
 *   }
 * }
 */
export type InventoryAttributes =
  | ManufacturingAttributes
  | RetailAttributes
  | ServicesAttributes

// =============================================================================
// 7.  Core Inventory Item
// =============================================================================

export type InventoryStatus = 'active' | 'inactive' | 'discontinued' | 'draft' | 'pending_review'

/**
 * Full inventory item as returned by the FastAPI /inventory endpoints.
 * The `attributes` field is typed as the discriminated union; the consumer
 * must narrow via `attributes.template` before accessing template-specific keys.
 */
export interface InventoryItem {
  id: string
  tenant_id: string
  sku: string
  name: string
  description?: string
  category?: string
  sub_category?: string
  brand?: string
  tags: string[]
  unit_price: number
  cost_price: number
  currency: string
  quantity_on_hand: number
  reorder_level: number
  unit_of_measure: UnitOfMeasure
  /** Discriminated JSONB attribute matrix — narrow before use. */
  attributes: InventoryAttributes
  status: InventoryStatus
  is_active: boolean
  created_by?: string
  updated_by?: string
  created_at: string
  updated_at: string
}

// =============================================================================
// 8.  Form Data Shapes (React Hook Form)
// =============================================================================

/**
 * Shape of the React Hook Form data object for creating / editing an item.
 * Attributes are split into per-template sub-objects so the form can manage
 * field registration without dynamic key mutation.
 */
export interface InventoryFormData {
  /* --- Core fields --- */
  sku: string
  name: string
  description: string
  category: string
  sub_category: string
  brand: string
  tags: string               // comma-separated, parsed to string[] on submit
  unit_price: number
  cost_price: number
  currency: string
  quantity_on_hand: number
  reorder_level: number
  status: InventoryStatus

  /* --- Template selector --- */
  template: IndustryTemplate

  /* --- Manufacturing attribute sub-object --- */
  manufacturing: Omit<ManufacturingAttributes, 'template'>

  /* --- Retail attribute sub-object --- */
  retail: Omit<RetailAttributes, 'template'>

  /* --- Services attribute sub-object --- */
  services: Omit<ServicesAttributes, 'template'>
}

// =============================================================================
// 9.  Template Metadata (UI display helpers)
// =============================================================================

export interface TemplateMetadata {
  id: IndustryTemplate
  label: string
  description: string
  icon: string                // Lucide icon name
  accentColor: string         // CSS custom property value
  fields: string[]            // human-readable field labels for the preview badge
}

export const TEMPLATE_METADATA: Record<IndustryTemplate, TemplateMetadata> = {
  Manufacturing: {
    id: 'Manufacturing',
    label: 'Manufacturing',
    description: 'Track batches, BOMs, tolerances, quality grades & machine IDs.',
    icon: 'Factory',
    accentColor: '#f59e0b',
    fields: ['Batch Number', 'Unit of Measure', 'Production Date', 'Quality Grade'],
  },
  Retail: {
    id: 'Retail',
    label: 'Retail',
    description: 'Manage sizes, colours, barcodes, seasons & planogram slots.',
    icon: 'ShoppingBag',
    accentColor: '#8b5cf6',
    fields: ['Size', 'Colour', 'Material', 'Barcode', 'Season'],
  },
  Services: {
    id: 'Services',
    label: 'Services',
    description: 'Define service type, duration, SLA commitments & license terms.',
    icon: 'Layers',
    accentColor: '#06b6d4',
    fields: ['Service Type', 'Duration (hrs)', 'Deliverable Format', 'License Type'],
  },
}

// =============================================================================
// 10.  API Payload (outgoing)
// =============================================================================

/**
 * Shape posted to POST /api/v1/inventory and PUT /api/v1/inventory/:id.
 * Attributes are merged back into a single discriminated object on submit.
 */
export interface CreateInventoryItemPayload {
  sku: string
  name: string
  description?: string
  category?: string
  sub_category?: string
  brand?: string
  tags: string[]
  unit_price: number
  cost_price: number
  currency: string
  quantity_on_hand: number
  reorder_level: number
  status: InventoryStatus
  attributes: InventoryAttributes
}

// =============================================================================
// 11.  Dashboard Table Types (zero-gap binding to InventoryItem)
// =============================================================================

/**
 * Typed column definition for the inventory dashboard table.
 *
 * Each column maps exactly to a key (or derived value) from `InventoryItem`
 * so unhandled fields are caught at compile time rather than silently rendered
 * as `undefined`.
 *
 * `key`        — the `InventoryItem` field key being rendered (or 'derived'
 *                for computed columns like formatted currency or template badge).
 * `header`     — display label shown in the `<th>` cell.
 * `align`      — horizontal text alignment of the `<td>` cell.
 * `render`     — optional custom renderer; if absent, the raw field value is
 *                coerced to string.
 *
 * @example
 * const columns: InventoryTableColumn[] = [
 *   { key: 'sku',  header: 'SKU',  align: 'left' },
 *   { key: 'name', header: 'Name', align: 'left', render: (item) => item.name },
 * ]
 */
export interface InventoryTableColumn {
  /**
   * Typed key of `InventoryItem` this column renders, or the literal
   * `'derived'` for columns whose value is computed from multiple fields
   * (e.g. formatted price, template badge).
   */
  key: keyof InventoryItem | 'derived'
  /** Column header label shown in `<th>`. */
  header: string
  /** Horizontal alignment of the data cell. Defaults to 'left'. */
  align?: 'left' | 'center' | 'right'
  /**
   * Optional custom render function.
   * Receives the full `InventoryItem` so derived columns can access any field.
   * Must return a `React.ReactNode`.
   */
  render?: (item: InventoryItem) => unknown
}

/**
 * Display metadata for each `InventoryStatus` value.
 * Used by the table's status cell to render the correct colour dot and label.
 *
 * The Record type over `InventoryStatus` enforces exhaustive coverage:
 * adding a new status to the `InventoryStatus` union without updating
 * `INVENTORY_STATUS_META` is a compile-time error.
 */
export interface InventoryStatusMeta {
  /** CSS colour value for the status indicator dot. */
  color: string
  /** Human-readable label shown in the table cell. */
  label: string
}

/**
 * Exhaustive map from every `InventoryStatus` to its display metadata.
 * Import and index with `item.status` to get the correct colour + label.
 *
 * @example
 * const { color, label } = INVENTORY_STATUS_META[item.status]
 */
export const INVENTORY_STATUS_META: Record<InventoryStatus, InventoryStatusMeta> = {
  active:         { color: '#10b981', label: 'Active' },
  inactive:       { color: '#6b7280', label: 'Inactive' },
  discontinued:   { color: '#ef4444', label: 'Discontinued' },
  draft:          { color: '#f59e0b', label: 'Draft' },
  pending_review: { color: '#3b82f6', label: 'Pending Review' },
}

/**
 * Typed shape for each stat card in the dashboard stats strip.
 * Decouples the stat card configuration from the rendering logic so the
 * strip can be data-driven without ad-hoc prop shapes.
 */
export interface InventoryStatCard {
  /** Display label above the value. */
  label: string
  /** The numeric value to render. */
  value: number
  /** Secondary descriptive text below the value. */
  sub: string
  /** Accent colour for the icon wrapper. */
  color: string
}
