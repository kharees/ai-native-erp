/**
 * types/finance.ts
 * ================
 * TypeScript definitions for the AI Copilot Ledger & Finance Engine.
 * Matches backend Pydantic schemas defined in backend/app/schemas/finance.py
 */

export type TransactionType = 'INCOME' | 'EXPENSE'

export interface FinanceLedgerBase {
  transaction_type: TransactionType
  category: string
  amount: number
  currency?: string
  description?: string
  metadata_insights?: Record<string, any>
}

export interface CreateFinanceLedgerPayload extends FinanceLedgerBase {}

export interface FinanceLedgerResponse extends FinanceLedgerBase {
  id: string
  tenant_id: string
  entry_date: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface FinanceSummaryResponse {
  tenant_id: string
  total_income: number
  total_expense: number
  net_balance: number
  currency: string
}
