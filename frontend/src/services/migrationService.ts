/**
 * services/migrationService.ts
 * ============================
 * Phase 8 — Async client service layer for the Enterprise Data Migration Hub.
 *
 * Maps to backend router: `/api/v1/migration`
 * The `X-Tenant-ID` header is automatically injected by `apiClient` interceptors.
 */

import apiClient from '@/lib/apiClient'
import type { DataMigrationLogResponse } from '@/types/migration'


const MIGRATION_BASE = '/api/v1/migration'

/**
 * Triggers a bulk data import by uploading a CSV/Excel file payload.
 * 
 * Maps to: `POST /api/v1/migration/import`
 * 
 * @param file - The File object originating from a file input element.
 * @returns The initialized DataMigrationLogResponse tracking object.
 */
export async function triggerBulkImport(
  file: File
): Promise<DataMigrationLogResponse> {
  // Using FormData since we are uploading multipart/form-data
  const formData = new FormData()
  formData.append('file', file)

  const response = await apiClient.post<DataMigrationLogResponse>(
    `${MIGRATION_BASE}/import`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  )
  return response.data
}

export const migrationService = {
  triggerBulkImport,
} as const
