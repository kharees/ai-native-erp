/**
 * types/migration.ts
 * ==================
 * TypeScript definitions for the Enterprise Data Migration Hub.
 * Matches backend Pydantic schemas defined in backend/app/schemas/migration.py
 */

export type MigrationStatus = 
  | 'INITIALIZED'
  | 'IN_PROGRESS'
  | 'SUCCESS'
  | 'FAILED'

export interface DataMigrationLogBase {
  source_file_name: string
  row_count_processed: number
}

export interface DataMigrationLogResponse extends DataMigrationLogBase {
  id: string
  tenant_id: string
  migration_status: MigrationStatus
  error_log_dump?: string
  is_active: boolean
  created_at: string
  updated_at: string
}
