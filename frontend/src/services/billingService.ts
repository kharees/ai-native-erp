/**
 * services/billingService.ts
 * ==========================
 * Phase 8 — Async client service layer for the Billing & Invoice module.
 *
 * Maps to backend router: `/api/v1/billing`
 * The `X-Tenant-ID` header is automatically injected by `apiClient` interceptors.
 */

import apiClient from '@/lib/apiClient'
import type {
  CreateBillingInvoicePayload,
  BillingInvoiceResponse,
} from '@/types/billing'


const BILLING_BASE = '/api/v1/billing'

/**
 * Creates a new billing invoice in the backend.
 * 
 * Maps to: `POST /api/v1/billing/`
 * 
 * @param payload - The invoice payload containing financials and items.
 * @returns The newly created BillingInvoiceResponse object.
 */
export async function createInvoice(
  payload: CreateBillingInvoicePayload
): Promise<BillingInvoiceResponse> {
  const response = await apiClient.post<BillingInvoiceResponse>(
    `${BILLING_BASE}/`,
    payload
  )
  return response.data
}

/**
 * Fetches the paginated history of invoices for the active tenant.
 * 
 * Maps to: `GET /api/v1/billing/`
 * 
 * @param skip - Number of records to skip (default: 0)
 * @param limit - Maximum number of records to return (default: 100)
 * @returns Array of BillingInvoiceResponse objects.
 */
export async function fetchInvoiceHistory(
  skip: number = 0,
  limit: number = 100
): Promise<BillingInvoiceResponse[]> {
  const response = await apiClient.get<BillingInvoiceResponse[]>(
    `${BILLING_BASE}/`,
    { params: { skip, limit } }
  )
  return response.data
}

export const billingService = {
  createInvoice,
  fetchInvoiceHistory,
} as const
