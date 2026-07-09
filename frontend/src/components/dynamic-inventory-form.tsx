'use client'

/**
 * components/dynamic-inventory-form.tsx
 * ======================================
 * Dynamic inventory item creation / edit form for the AI-Native ERP.
 *
 * Architecture:
 *  • React Hook Form manages all field state with a unified InventoryFormData shape.
 *  • Zod validates fields on submit; errors are displayed inline under each input.
 *  • The "template" field is a discriminant — selecting Manufacturing / Retail /
 *    Services swaps the visible attribute panel while keeping the other panels'
 *    values in the form state (no data loss on tab switch).
 *  • The CSS module provides all styling — no Tailwind required.
 *
 * Dependencies (all in package.json):
 *    react-hook-form, @hookform/resolvers, zod, lucide-react
 */

import React, { useState } from 'react'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Factory, ShoppingBag, Layers, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react'

import type {
  IndustryTemplate,
  InventoryAttributes,
  CreateInventoryItemPayload,
} from '@/types/inventory'
import { TEMPLATE_METADATA } from '@/types/inventory'
import styles from './dynamic-inventory-form.module.css'

// =============================================================================
// Zod Schema
// =============================================================================

/** Manufacturing attribute sub-schema. */
const manufacturingSchema = z.object({
  batch_number:        z.string().min(1, 'Batch number is required'),
  unit_of_measure:     z.string().min(1, 'Unit of measure is required'),
  production_date:     z.string().min(1, 'Production date is required'),
  expiry_date:         z.string().optional(),
  quality_grade:       z.enum(['A', 'B', 'C', 'rejected']).default('A'),
  raw_material_source: z.string().optional(),
  machine_id:          z.string().optional(),
  tolerances:          z.string().optional(),
  bom_reference:       z.string().optional(),
  certification:       z.string().optional(),
  hazmat_code:         z.string().optional(),
  weight_kg:           z.coerce.number().nonnegative().optional(),
  volume_m3:           z.coerce.number().nonnegative().optional(),
})

/** Retail attribute sub-schema. */
const retailSchema = z.object({
  size:               z.string().min(1, 'Size is required'),
  color:              z.string().min(1, 'Colour is required'),
  material:           z.string().optional(),
  brand_line:         z.string().optional(),
  barcode:            z.string().optional(),
  season:             z.enum(['spring_summer', 'autumn_winter', 'all_season', 'limited_edition']).optional(),
  gender:             z.enum(['men', 'women', 'unisex', 'kids', 'na']).optional(),
  style_code:         z.string().optional(),
  country_of_origin:  z.string().max(2).optional(),
  mrp:                z.coerce.number().nonnegative().optional(),
  discount_pct:       z.coerce.number().min(0).max(100).optional(),
  shelf_min_qty:      z.coerce.number().int().nonnegative().optional(),
  planogram_slot:     z.string().optional(),
})

/** Services attribute sub-schema. */
const servicesSchema = z.object({
  service_type:            z.string().min(1, 'Service type is required'),
  service_duration_hours:  z.coerce.number().positive('Duration must be > 0'),
  deliverable_format:      z.string().optional(),
  team_size:               z.coerce.number().int().positive().optional(),
  license_type:            z.enum([
    'perpetual', 'subscription_monthly', 'subscription_annual',
    'pay_per_use', 'open_source', 'custom',
  ]).optional(),
  renewal_period_days:     z.coerce.number().int().positive().optional(),
  max_seats:               z.coerce.number().int().positive().optional(),
  sla_response_hours:      z.coerce.number().nonnegative().optional(),
  sla_uptime_pct:          z.coerce.number().min(0).max(100).optional(),
  sow_url:                 z.string().url('Must be a valid URL').optional().or(z.literal('')),
})

/** Root form schema — all fields validated together on submit. */
const inventoryFormSchema = z.object({
  sku:              z.string().min(1, 'SKU is required').max(64),
  name:             z.string().min(2, 'Name must be at least 2 characters').max(255),
  description:      z.string().max(2000).optional().default(''),
  category:         z.string().max(128).optional().default(''),
  sub_category:     z.string().max(128).optional().default(''),
  brand:            z.string().max(128).optional().default(''),
  tags:             z.string().optional().default(''),
  unit_price:       z.coerce.number().nonnegative('Must be ≥ 0'),
  cost_price:       z.coerce.number().nonnegative('Must be ≥ 0'),
  currency:         z.string().length(3, 'Enter a 3-letter currency code').default('USD'),
  quantity_on_hand: z.coerce.number().int().nonnegative('Must be ≥ 0'),
  reorder_level:    z.coerce.number().int().nonnegative('Must be ≥ 0'),
  status:           z.enum(['active', 'inactive', 'discontinued', 'draft', 'pending_review']).default('draft'),
  template:         z.enum(['Manufacturing', 'Retail', 'Services']),
  manufacturing:    manufacturingSchema,
  retail:           retailSchema,
  services:         servicesSchema,
})

type FormValues = z.infer<typeof inventoryFormSchema>

// =============================================================================
// Default values
// =============================================================================

const DEFAULT_VALUES: FormValues = {
  sku: '', name: '', description: '', category: '', sub_category: '',
  brand: '', tags: '', unit_price: 0, cost_price: 0, currency: 'USD',
  quantity_on_hand: 0, reorder_level: 0, status: 'draft',
  template: 'Manufacturing',
  manufacturing: {
    batch_number: '', unit_of_measure: 'unit', production_date: '',
    quality_grade: 'A',
  },
  retail: { size: '', color: '' },
  services: { service_type: '', service_duration_hours: 1 },
}

// =============================================================================
// Tiny helpers
// =============================================================================

const cx = (...cls: (string | undefined | false)[]): string =>
  cls.filter(Boolean).join(' ')

function Err({ msg }: { msg?: string }) {
  if (!msg) return null
  return (
    <span className={styles.errorMsg}>
      <AlertCircle size={12} /> {msg}
    </span>
  )
}

// =============================================================================
// Template Selector
// =============================================================================

interface TemplateSelectorProps {
  value: IndustryTemplate
  onChange: (t: IndustryTemplate) => void
}

function TemplateSelector({ value, onChange }: TemplateSelectorProps) {
  const icons: Record<IndustryTemplate, React.ReactNode> = {
    Manufacturing: <Factory size={18} />,
    Retail:        <ShoppingBag size={18} />,
    Services:      <Layers size={18} />,
  }

  const activeClass: Record<IndustryTemplate, string> = {
    Manufacturing: styles.activeMfg,
    Retail:        styles.activeRetail,
    Services:      styles.activeSvc,
  }

  return (
    <div className={styles.templateGrid}>
      {(Object.keys(TEMPLATE_METADATA) as IndustryTemplate[]).map((id) => {
        const meta = TEMPLATE_METADATA[id]
        const isActive = value === id
        return (
          <button
            key={id}
            type="button"
            className={cx(styles.templateCard, isActive && activeClass[id])}
            onClick={() => onChange(id)}
            aria-pressed={isActive}
          >
            {/* Icon bubble */}
            <div
              className={styles.templateIcon}
              style={{
                background: isActive
                  ? `rgba(${hexToRgb(meta.accentColor)}, 0.18)`
                  : 'rgba(255,255,255,0.04)',
                color: isActive ? meta.accentColor : '#5a5a80',
              }}
            >
              {icons[id]}
            </div>

            <p className={styles.templateLabel}>{meta.label}</p>
            <p className={styles.templateDesc}>{meta.description}</p>

            {/* Active check */}
            {isActive && (
              <span
                className={styles.templateBadge}
                style={{ background: meta.accentColor }}
              >
                <CheckCircle2 size={12} color="#fff" />
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}

/** Convert #rrggbb → "r, g, b" for CSS rgba(). */
function hexToRgb(hex: string): string {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `${r}, ${g}, ${b}`
}

// =============================================================================
// Manufacturing Attribute Panel
// =============================================================================

function ManufacturingPanel({ form }: { form: ReturnType<typeof useForm<FormValues>> }) {
  const { register, formState: { errors } } = form
  const e = errors.manufacturing

  return (
    <div className={styles.attributePanel}>
      <div
        className={styles.panelAccentBar}
        style={{ background: 'linear-gradient(90deg, #f59e0b, #fbbf24)' }}
      />

      <p className={styles.sectionTitle}>Manufacturing Attributes</p>

      {/* Row 1 */}
      <div className={styles.grid2} style={{ marginBottom: 16 }}>
        <div className={styles.fieldGroup}>
          <label className={styles.label}>
            Batch Number <span className={styles.required}>*</span>
          </label>
          <input
            className={cx(styles.input, e?.batch_number && styles.hasError)}
            placeholder="BT-2024-00412"
            {...register('manufacturing.batch_number')}
          />
          <Err msg={e?.batch_number?.message} />
        </div>

        <div className={styles.fieldGroup}>
          <label className={styles.label}>
            Unit of Measure <span className={styles.required}>*</span>
          </label>
          <select
            className={cx(styles.select, e?.unit_of_measure && styles.hasError)}
            {...register('manufacturing.unit_of_measure')}
          >
            {['unit','kg','g','mg','l','ml','m','cm','mm','m2','m3','box','pallet','dozen','pack'].map(u => (
              <option key={u} value={u}>{u}</option>
            ))}
          </select>
          <Err msg={e?.unit_of_measure?.message} />
        </div>
      </div>

      {/* Row 2 */}
      <div className={styles.grid2} style={{ marginBottom: 16 }}>
        <div className={styles.fieldGroup}>
          <label className={styles.label}>
            Production Date <span className={styles.required}>*</span>
          </label>
          <input
            type="date"
            className={cx(styles.input, e?.production_date && styles.hasError)}
            {...register('manufacturing.production_date')}
          />
          <Err msg={e?.production_date?.message} />
        </div>

        <div className={styles.fieldGroup}>
          <label className={styles.label}>Expiry / Best-Before Date</label>
          <input
            type="date"
            className={styles.input}
            {...register('manufacturing.expiry_date')}
          />
        </div>
      </div>

      {/* Row 3 */}
      <div className={styles.grid3} style={{ marginBottom: 16 }}>
        <div className={styles.fieldGroup}>
          <label className={styles.label}>
            Quality Grade <span className={styles.required}>*</span>
          </label>
          <select className={styles.select} {...register('manufacturing.quality_grade')}>
            <option value="A">Grade A — Premium</option>
            <option value="B">Grade B — Standard</option>
            <option value="C">Grade C — Acceptable</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>

        <div className={styles.fieldGroup}>
          <label className={styles.label}>Machine / Asset ID</label>
          <input
            className={styles.input}
            placeholder="CNC-07"
            {...register('manufacturing.machine_id')}
          />
        </div>

        <div className={styles.fieldGroup}>
          <label className={styles.label}>BOM Reference</label>
          <input
            className={styles.input}
            placeholder="BOM-0042"
            {...register('manufacturing.bom_reference')}
          />
        </div>
      </div>

      {/* Row 4 */}
      <div className={styles.grid3} style={{ marginBottom: 16 }}>
        <div className={styles.fieldGroup}>
          <label className={styles.label}>Raw Material Source</label>
          <input
            className={styles.input}
            placeholder="Supplier / Plant name"
            {...register('manufacturing.raw_material_source')}
          />
        </div>

        <div className={styles.fieldGroup}>
          <label className={styles.label}>Tolerances</label>
          <input
            className={styles.input}
            placeholder="±0.05mm"
            {...register('manufacturing.tolerances')}
          />
        </div>

        <div className={styles.fieldGroup}>
          <label className={styles.label}>Certification</label>
          <input
            className={styles.input}
            placeholder="ISO 9001"
            {...register('manufacturing.certification')}
          />
        </div>
      </div>

      {/* Row 5 */}
      <div className={styles.grid3}>
        <div className={styles.fieldGroup}>
          <label className={styles.label}>Hazmat Code (UN)</label>
          <input
            className={styles.input}
            placeholder="UN1263"
            {...register('manufacturing.hazmat_code')}
          />
        </div>

        <div className={styles.fieldGroup}>
          <label className={styles.label}>Weight (kg)</label>
          <input
            type="number" step="0.001"
            className={styles.input}
            placeholder="0.000"
            {...register('manufacturing.weight_kg')}
          />
        </div>

        <div className={styles.fieldGroup}>
          <label className={styles.label}>Volume (m³)</label>
          <input
            type="number" step="0.0001"
            className={styles.input}
            placeholder="0.0000"
            {...register('manufacturing.volume_m3')}
          />
        </div>
      </div>
    </div>
  )
}

// =============================================================================
// Retail Attribute Panel
// =============================================================================

function RetailPanel({ form }: { form: ReturnType<typeof useForm<FormValues>> }) {
  const { register, formState: { errors } } = form
  const e = errors.retail

  return (
    <div className={styles.attributePanel}>
      <div
        className={styles.panelAccentBar}
        style={{ background: 'linear-gradient(90deg, #7c3aed, #8b5cf6, #a78bfa)' }}
      />

      <p className={styles.sectionTitle}>Retail Attributes</p>

      {/* Row 1 */}
      <div className={styles.grid3} style={{ marginBottom: 16 }}>
        <div className={styles.fieldGroup}>
          <label className={styles.label}>
            Size <span className={styles.required}>*</span>
          </label>
          <input
            className={cx(styles.input, e?.size && styles.hasError)}
            placeholder="S / M / L / XL / 42"
            {...register('retail.size')}
          />
          <Err msg={e?.size?.message} />
        </div>

        <div className={styles.fieldGroup}>
          <label className={styles.label}>
            Colour <span className={styles.required}>*</span>
          </label>
          <input
            className={cx(styles.input, e?.color && styles.hasError)}
            placeholder="Midnight Black"
            {...register('retail.color')}
          />
          <Err msg={e?.color?.message} />
        </div>

        <div className={styles.fieldGroup}>
          <label className={styles.label}>Material</label>
          <input
            className={styles.input}
            placeholder="80% cotton, 20% polyester"
            {...register('retail.material')}
          />
        </div>
      </div>

      {/* Row 2 */}
      <div className={styles.grid3} style={{ marginBottom: 16 }}>
        <div className={styles.fieldGroup}>
          <label className={styles.label}>Brand Line / Collection</label>
          <input
            className={styles.input}
            placeholder="ERP Wear SS25"
            {...register('retail.brand_line')}
          />
        </div>

        <div className={styles.fieldGroup}>
          <label className={styles.label}>Barcode (EAN / GTIN)</label>
          <input
            className={styles.input}
            placeholder="8901234567890"
            {...register('retail.barcode')}
          />
        </div>

        <div className={styles.fieldGroup}>
          <label className={styles.label}>Style Code</label>
          <input
            className={styles.input}
            placeholder="STY-2024-001"
            {...register('retail.style_code')}
          />
        </div>
      </div>

      {/* Row 3 */}
      <div className={styles.grid3} style={{ marginBottom: 16 }}>
        <div className={styles.fieldGroup}>
          <label className={styles.label}>Season</label>
          <select className={styles.select} {...register('retail.season')}>
            <option value="">— Select season —</option>
            <option value="spring_summer">Spring / Summer</option>
            <option value="autumn_winter">Autumn / Winter</option>
            <option value="all_season">All Season</option>
            <option value="limited_edition">Limited Edition</option>
          </select>
        </div>

        <div className={styles.fieldGroup}>
          <label className={styles.label}>Gender Segment</label>
          <select className={styles.select} {...register('retail.gender')}>
            <option value="na">Not Applicable</option>
            <option value="men">Men</option>
            <option value="women">Women</option>
            <option value="unisex">Unisex</option>
            <option value="kids">Kids</option>
          </select>
        </div>

        <div className={styles.fieldGroup}>
          <label className={styles.label}>Country of Origin (ISO)</label>
          <input
            className={styles.input}
            maxLength={2}
            placeholder="IN"
            {...register('retail.country_of_origin')}
          />
          <span className={styles.hint}>2-letter ISO 3166-1 code, e.g. IN, CN, US</span>
        </div>
      </div>

      {/* Row 4 */}
      <div className={styles.grid3}>
        <div className={styles.fieldGroup}>
          <label className={styles.label}>MRP (Retail Price)</label>
          <input
            type="number" step="0.01"
            className={styles.input}
            placeholder="0.00"
            {...register('retail.mrp')}
          />
        </div>

        <div className={styles.fieldGroup}>
          <label className={styles.label}>Discount %</label>
          <input
            type="number" step="0.1" min="0" max="100"
            className={styles.input}
            placeholder="0.0"
            {...register('retail.discount_pct')}
          />
          <Err msg={e?.discount_pct?.message} />
        </div>

        <div className={styles.fieldGroup}>
          <label className={styles.label}>Shelf Min Qty</label>
          <input
            type="number" step="1" min="0"
            className={styles.input}
            placeholder="0"
            {...register('retail.shelf_min_qty')}
          />
        </div>
      </div>
    </div>
  )
}

// =============================================================================
// Services Attribute Panel
// =============================================================================

function ServicesPanel({ form }: { form: ReturnType<typeof useForm<FormValues>> }) {
  const { register, formState: { errors } } = form
  const e = errors.services

  return (
    <div className={styles.attributePanel}>
      <div
        className={styles.panelAccentBar}
        style={{ background: 'linear-gradient(90deg, #0891b2, #06b6d4, #67e8f9)' }}
      />

      <p className={styles.sectionTitle}>Services Attributes</p>

      {/* Row 1 */}
      <div className={styles.grid2} style={{ marginBottom: 16 }}>
        <div className={styles.fieldGroup}>
          <label className={styles.label}>
            Service Type <span className={styles.required}>*</span>
          </label>
          <input
            className={cx(styles.input, e?.service_type && styles.hasError)}
            placeholder="Consulting / SaaS / Implementation"
            {...register('services.service_type')}
          />
          <Err msg={e?.service_type?.message} />
        </div>

        <div className={styles.fieldGroup}>
          <label className={styles.label}>
            Duration (hours) <span className={styles.required}>*</span>
          </label>
          <input
            type="number" step="0.5" min="0.5"
            className={cx(styles.input, e?.service_duration_hours && styles.hasError)}
            placeholder="40"
            {...register('services.service_duration_hours')}
          />
          <Err msg={e?.service_duration_hours?.message} />
        </div>
      </div>

      {/* Row 2 */}
      <div className={styles.grid1} style={{ marginBottom: 16 }}>
        <div className={styles.fieldGroup}>
          <label className={styles.label}>Deliverable Format</label>
          <textarea
            className={styles.textarea}
            placeholder="PDF Report + Working Prototype + 60 days support"
            {...register('services.deliverable_format')}
          />
        </div>
      </div>

      {/* Row 3 */}
      <div className={styles.grid3} style={{ marginBottom: 16 }}>
        <div className={styles.fieldGroup}>
          <label className={styles.label}>License Type</label>
          <select className={styles.select} {...register('services.license_type')}>
            <option value="">— Select license —</option>
            <option value="perpetual">Perpetual</option>
            <option value="subscription_monthly">Subscription — Monthly</option>
            <option value="subscription_annual">Subscription — Annual</option>
            <option value="pay_per_use">Pay-Per-Use</option>
            <option value="open_source">Open Source</option>
            <option value="custom">Custom Agreement</option>
          </select>
        </div>

        <div className={styles.fieldGroup}>
          <label className={styles.label}>Renewal Period (days)</label>
          <input
            type="number" step="1" min="1"
            className={styles.input}
            placeholder="365"
            {...register('services.renewal_period_days')}
          />
        </div>

        <div className={styles.fieldGroup}>
          <label className={styles.label}>Max Seats / Users</label>
          <input
            type="number" step="1" min="1"
            className={styles.input}
            placeholder="50"
            {...register('services.max_seats')}
          />
        </div>
      </div>

      {/* Row 4 */}
      <div className={styles.grid3} style={{ marginBottom: 16 }}>
        <div className={styles.fieldGroup}>
          <label className={styles.label}>Team Size</label>
          <input
            type="number" step="1" min="1"
            className={styles.input}
            placeholder="3"
            {...register('services.team_size')}
          />
        </div>

        <div className={styles.fieldGroup}>
          <label className={styles.label}>SLA Response (hrs)</label>
          <input
            type="number" step="0.5" min="0"
            className={styles.input}
            placeholder="4"
            {...register('services.sla_response_hours')}
          />
          <span className={styles.hint}>e.g. 4 hrs for P1</span>
        </div>

        <div className={styles.fieldGroup}>
          <label className={styles.label}>SLA Uptime (%)</label>
          <input
            type="number" step="0.01" min="0" max="100"
            className={styles.input}
            placeholder="99.9"
            {...register('services.sla_uptime_pct')}
          />
        </div>
      </div>

      {/* Row 5 */}
      <div className={styles.grid1}>
        <div className={styles.fieldGroup}>
          <label className={styles.label}>Scope-of-Work URL</label>
          <input
            type="url"
            className={cx(styles.input, e?.sow_url && styles.hasError)}
            placeholder="https://docs.example.com/sow-2024.pdf"
            {...register('services.sow_url')}
          />
          <Err msg={e?.sow_url?.message} />
        </div>
      </div>
    </div>
  )
}

// =============================================================================
// Props
// =============================================================================

export interface DynamicInventoryFormProps {
  /**
   * Called with the merged CreateInventoryItemPayload on successful validation.
   * Return a Promise to have the submit button show a loading spinner.
   */
  onSubmit?: (payload: CreateInventoryItemPayload) => Promise<void> | void
  /** Pre-fill form values for edit mode. */
  defaultValues?: Partial<FormValues>
  /** If true, renders in a compact read-only review mode (future). */
  readOnly?: boolean
}

// =============================================================================
// Main Component
// =============================================================================

/**
 * DynamicInventoryForm
 * --------------------
 * A fully controlled, validated inventory form that switches its attribute
 * panel between Manufacturing / Retail / Services based on the `template`
 * discriminant field.
 *
 * @example
 * <DynamicInventoryForm
 *   onSubmit={async (payload) => {
 *     await api.post('/api/v1/inventory', payload)
 *   }}
 * />
 */
export default function DynamicInventoryForm({
  onSubmit,
  defaultValues,
}: DynamicInventoryFormProps) {
  const [submitting, setSubmitting] = useState(false)
  const [success, setSuccess] = useState(false)

  const form = useForm<FormValues>({
    resolver: zodResolver(inventoryFormSchema),
    defaultValues: { ...DEFAULT_VALUES, ...defaultValues },
    mode: 'onBlur',
  })

  const {
    register,
    control,
    handleSubmit,
    watch,
    reset,
    formState: { errors },
  } = form

  const template = watch('template')
  const tagsRaw  = watch('tags')
  const tagList  = tagsRaw
    ? tagsRaw.split(',').map((t) => t.trim()).filter(Boolean)
    : []

  // -------------------------------------------------------------------------
  // Submit handler — merge attribute sub-objects into the discriminated union
  // -------------------------------------------------------------------------
  const handleFormSubmit = async (values: FormValues) => {
    let attributes: InventoryAttributes

    if (values.template === 'Manufacturing') {
      attributes = { template: 'Manufacturing', ...values.manufacturing } as InventoryAttributes
    } else if (values.template === 'Retail') {
      attributes = { template: 'Retail', ...values.retail } as InventoryAttributes
    } else {
      attributes = { template: 'Services', ...values.services } as InventoryAttributes
    }

    const payload: CreateInventoryItemPayload = {
      sku:              values.sku,
      name:             values.name,
      description:      values.description || undefined,
      category:         values.category    || undefined,
      sub_category:     values.sub_category|| undefined,
      brand:            values.brand       || undefined,
      tags:             tagList,
      unit_price:       values.unit_price,
      cost_price:       values.cost_price,
      currency:         values.currency,
      quantity_on_hand: values.quantity_on_hand,
      reorder_level:    values.reorder_level,
      status:           values.status,
      attributes,
    }

    setSubmitting(true)
    try {
      await onSubmit?.(payload)
      setSuccess(true)
      setTimeout(() => setSuccess(false), 4000)
    } finally {
      setSubmitting(false)
    }
  }

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------
  return (
    <div className={styles.root}>
      <form onSubmit={handleSubmit(handleFormSubmit)} noValidate>

        {/* ── Template Selector ─────────────────────────────────────── */}
        <Controller
          name="template"
          control={control}
          render={({ field }) => (
            <TemplateSelector
              value={field.value as IndustryTemplate}
              onChange={field.onChange}
            />
          )}
        />

        {/* ── Core Item Details ─────────────────────────────────────── */}
        <div className={styles.formCard}>

          <div className={styles.section}>
            <p className={styles.sectionTitle}>Item Identity</p>
            <div className={styles.grid3} style={{ marginBottom: 16 }}>
              <div className={styles.fieldGroup}>
                <label className={styles.label}>
                  SKU <span className={styles.required}>*</span>
                </label>
                <input
                  className={cx(styles.input, errors.sku && styles.hasError)}
                  placeholder="ERP-SKU-001"
                  {...register('sku')}
                />
                <Err msg={errors.sku?.message} />
              </div>

              <div className={styles.fieldGroup} style={{ gridColumn: 'span 2' }}>
                <label className={styles.label}>
                  Item Name <span className={styles.required}>*</span>
                </label>
                <input
                  className={cx(styles.input, errors.name && styles.hasError)}
                  placeholder="Premium Widget v3"
                  {...register('name')}
                />
                <Err msg={errors.name?.message} />
              </div>
            </div>

            <div className={styles.grid1} style={{ marginBottom: 16 }}>
              <div className={styles.fieldGroup}>
                <label className={styles.label}>Description</label>
                <textarea
                  className={styles.textarea}
                  placeholder="Detailed product / service description…"
                  {...register('description')}
                />
              </div>
            </div>

            <div className={styles.grid3}>
              <div className={styles.fieldGroup}>
                <label className={styles.label}>Category</label>
                <input className={styles.input} placeholder="Electronics" {...register('category')} />
              </div>
              <div className={styles.fieldGroup}>
                <label className={styles.label}>Sub-Category</label>
                <input className={styles.input} placeholder="Semiconductors" {...register('sub_category')} />
              </div>
              <div className={styles.fieldGroup}>
                <label className={styles.label}>Brand</label>
                <input className={styles.input} placeholder="Acme Corp" {...register('brand')} />
              </div>
            </div>
          </div>

          {/* ── Pricing & Stock ─────────────────────────────────────── */}
          <div className={styles.section}>
            <p className={styles.sectionTitle}>Pricing &amp; Stock</p>
            <div className={styles.grid3} style={{ marginBottom: 16 }}>
              <div className={styles.fieldGroup}>
                <label className={styles.label}>
                  Unit Price <span className={styles.required}>*</span>
                </label>
                <input
                  type="number" step="0.01" min="0"
                  className={cx(styles.input, errors.unit_price && styles.hasError)}
                  placeholder="0.00"
                  {...register('unit_price')}
                />
                <Err msg={errors.unit_price?.message} />
              </div>

              <div className={styles.fieldGroup}>
                <label className={styles.label}>
                  Cost Price <span className={styles.required}>*</span>
                </label>
                <input
                  type="number" step="0.01" min="0"
                  className={cx(styles.input, errors.cost_price && styles.hasError)}
                  placeholder="0.00"
                  {...register('cost_price')}
                />
                <Err msg={errors.cost_price?.message} />
              </div>

              <div className={styles.fieldGroup}>
                <label className={styles.label}>Currency</label>
                <input
                  className={cx(styles.input, errors.currency && styles.hasError)}
                  maxLength={3}
                  placeholder="USD"
                  {...register('currency')}
                />
                <Err msg={errors.currency?.message} />
              </div>
            </div>

            <div className={styles.grid3}>
              <div className={styles.fieldGroup}>
                <label className={styles.label}>Qty on Hand</label>
                <input
                  type="number" step="1" min="0"
                  className={cx(styles.input, errors.quantity_on_hand && styles.hasError)}
                  placeholder="0"
                  {...register('quantity_on_hand')}
                />
                <Err msg={errors.quantity_on_hand?.message} />
              </div>

              <div className={styles.fieldGroup}>
                <label className={styles.label}>Reorder Level</label>
                <input
                  type="number" step="1" min="0"
                  className={styles.input}
                  placeholder="10"
                  {...register('reorder_level')}
                />
              </div>

              <div className={styles.fieldGroup}>
                <label className={styles.label}>Status</label>
                <select className={styles.select} {...register('status')}>
                  <option value="draft">Draft</option>
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                  <option value="pending_review">Pending Review</option>
                  <option value="discontinued">Discontinued</option>
                </select>
              </div>
            </div>
          </div>

          {/* ── Tags ────────────────────────────────────────────────── */}
          <div className={styles.section}>
            <p className={styles.sectionTitle}>Tags</p>
            <div className={styles.fieldGroup}>
              <label className={styles.label}>Tags (comma-separated)</label>
              <input
                className={styles.input}
                placeholder="perishable, cold-chain, hazmat"
                {...register('tags')}
              />
              <span className={styles.hint}>Press comma to separate tags</span>
              {tagList.length > 0 && (
                <div className={styles.tagList}>
                  {tagList.map((t) => <span key={t} className={styles.tag}>{t}</span>)}
                </div>
              )}
            </div>
          </div>

          {/* ── Dynamic Attribute Panel ──────────────────────────────── */}
          <div className={styles.section}>
            <p className={styles.sectionTitle}>
              {TEMPLATE_METADATA[template].label} Attributes
            </p>

            {template === 'Manufacturing' && <ManufacturingPanel form={form} />}
            {template === 'Retail'        && <RetailPanel        form={form} />}
            {template === 'Services'      && <ServicesPanel      form={form} />}
          </div>

          {/* ── Success Banner ───────────────────────────────────────── */}
          {success && (
            <div className={styles.successBanner}>
              <CheckCircle2 size={16} />
              Inventory item saved successfully!
            </div>
          )}

          {/* ── Action Row ───────────────────────────────────────────── */}
          <div className={styles.actionRow}>
            <button
              type="button"
              className={styles.btnGhost}
              onClick={() => reset(DEFAULT_VALUES)}
            >
              Reset
            </button>
            <button
              type="submit"
              className={styles.btnPrimary}
              disabled={submitting}
            >
              {submitting ? (
                <><Loader2 size={15} className="spin" /> Saving…</>
              ) : (
                'Save Item'
              )}
            </button>
          </div>

        </div>
      </form>
    </div>
  )
}
