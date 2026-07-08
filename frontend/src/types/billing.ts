/**
 * types/billing.ts
 * ================
 * TypeScript definitions for the Omnichannel Billing & Invoice Engine.
 * Matches backend Pydantic schemas defined in backend/app/schemas/billing.py
 */

export type PaymentStatus =
  | 'PENDING'
  | 'PAID'
  | 'OVERDUE'
  | 'CANCELLED'
  | 'FAILED'
  | 'REFUNDED'
  | 'PARTIAL'

export type PaymentMode =
  | 'UPI'
  | 'CASH'
  | 'CARD'
  | 'ONLINE'
  | 'CHEQUE'
  | 'BANK_TRANSFER'
  | 'WALLET'
  | 'EMI'
  | 'CREDIT'
  | 'OTHER'

export interface BillingItemSnapshot {
  sku: string
  name: string
  quantity: number
  unit_price: number
  line_total: number
  currency?: string
  tax_rate_pct: number
  tax_amount: number
  discount_pct?: number
  attributes?: Record<string, any>
}

export interface CreateBillingInvoicePayload {
  customer_name?: string
  customer_email?: string
  customer_phone?: string
  customer_gstin?: string
  billing_address?: string
  currency?: string
  subtotal: number
  tax_amount: number
  total_amount: number
  discount_amount?: number
  tax_rate_pct?: number
  gstin_seller?: string
  payment_mode?: PaymentMode
  items_snapshot: BillingItemSnapshot[]
  notes?: string
  invoice_metadata?: Record<string, any>
  payment_status?: PaymentStatus
  payment_reference?: string
  due_date?: string
}

export interface BillingInvoiceResponse extends CreateBillingInvoicePayload {
  id: string
  tenant_id: string
  invoice_number: string
  paid_at?: string
  is_active: boolean
  invoice_version: number
  created_at: string
  updated_at: string
}
