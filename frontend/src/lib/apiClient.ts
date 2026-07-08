/**
 * lib/apiClient.ts
 * ================
 * Singleton Axios instance for all FastAPI backend communication.
 *
 * Design
 * ------
 *  • Base URL is read from NEXT_PUBLIC_API_BASE_URL (set in .env.local).
 *  • A REQUEST interceptor injects the `X-Tenant-ID` header on every call,
 *    reading the tenant UUID from the module-level setter below.
 *    This keeps individual service functions clean — no manual header
 *    repetition across 20+ API calls.
 *  • A RESPONSE interceptor normalises HTTP errors into a typed ApiError
 *    object so every catch block has a consistent shape.
 *  • Timeout defaults to 15 s; can be overridden per-call.
 */

import axios, {
  AxiosError,
  AxiosInstance,
  AxiosResponse,
  InternalAxiosRequestConfig,
} from 'axios'

// =============================================================================
// 1.  Tenant context — set once after auth resolves
// =============================================================================

/**
 * Module-level tenant UUID store.
 * Call `setActiveTenant(uuid)` after the user's session resolves.
 * The request interceptor reads this on every outgoing call.
 */
let _activeTenantId: string | null = null

/** Write the active tenant UUID into the module store. */
export function setActiveTenant(tenantId: string): void {
  _activeTenantId = tenantId
}

/** Read the currently active tenant UUID. */
export function getActiveTenant(): string | null {
  return _activeTenantId
}

// =============================================================================
// 2.  Typed API error
// =============================================================================

/**
 * Normalised error shape thrown by the response interceptor.
 * All service-layer catch blocks can rely on this interface.
 */
export interface ApiError {
  /** HTTP status code (0 = network error / no response). */
  status: number
  /** Machine-readable error code from the FastAPI response body. */
  code: string
  /** Human-readable message safe to display in the UI. */
  message: string
  /** Raw response body (for debugging). */
  detail?: unknown
}

/** Type-guard: is this an ApiError? */
export function isApiError(err: unknown): err is ApiError {
  return (
    typeof err === 'object' &&
    err !== null &&
    'status' in err &&
    'code' in err &&
    'message' in err
  )
}

// =============================================================================
// 3.  Axios instance
// =============================================================================

const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 15_000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
})

// =============================================================================
// 4.  Request interceptor — inject X-Tenant-ID
// =============================================================================

import { useAuthStore } from '@/store/authStore'

apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig): InternalAxiosRequestConfig => {
    const authState = useAuthStore.getState();
    const token = authState.accessToken;
    const tenantId = authState.user?.tenant_id || _activeTenantId;

    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    
    if (tenantId) {
      config.headers['X-Tenant-ID'] = tenantId;
    }
    return config
  },
  (error: unknown) => Promise.reject(error),
)

// =============================================================================
// 5.  Response interceptor — normalise errors
// =============================================================================

apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError<{ error?: string; detail?: unknown }>): never => {
    const status = error.response?.status ?? 0
    const body   = error.response?.data

    const apiError: ApiError = {
      status,
      code:    body?.error ?? 'network_error',
      message: typeof body?.detail === 'string'
        ? body.detail
        : error.message ?? 'An unexpected error occurred.',
      detail: body?.detail,
    }

    throw apiError
  },
)

export default apiClient
