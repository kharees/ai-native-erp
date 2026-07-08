/**
 * services/financeService.ts
 * ==========================
 * Phase 8 — Async client service layer for the AI Copilot Ledger & Finance module.
 *
 * Maps to backend router: `/api/v1/finance`
 * The `X-Tenant-ID` header is automatically injected by `apiClient` interceptors.
 */

import apiClient from '@/lib/apiClient'
import type {
  CreateFinanceLedgerPayload,
  FinanceLedgerResponse,
  FinanceSummaryResponse,
} from '@/types/finance'


const FINANCE_BASE = '/api/v1/finance'

/**
 * Records a new financial ledger transaction (INCOME or EXPENSE) with AI metadata.
 * 
 * Maps to: `POST /api/v1/finance/`
 * 
 * @param payload - The transaction payload.
 * @returns The newly created FinanceLedgerResponse object.
 */
export async function recordTransaction(
  payload: CreateFinanceLedgerPayload
): Promise<FinanceLedgerResponse> {
  const response = await apiClient.post<FinanceLedgerResponse>(
    `${FINANCE_BASE}/`,
    payload
  )
  return response.data
}

/**
 * Retrieves the aggregated multi-tenant financial summary for the active tenant.
 * Includes total income, total expense, and net balance calculated precisely by the backend.
 * 
 * Maps to: `GET /api/v1/finance/summary`
 * 
 * @returns FinanceSummaryResponse containing aggregated arrays.
 */
export async function getFinanceSummary(): Promise<FinanceSummaryResponse> {
  const response = await apiClient.get<FinanceSummaryResponse>(
    `${FINANCE_BASE}/summary`
  )
  return response.data
}

export const financeService = {
  recordTransaction,
  getFinanceSummary,
} as const
