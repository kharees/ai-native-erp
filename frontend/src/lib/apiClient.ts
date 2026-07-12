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
  // Required for the browser to send/receive the httpOnly refresh_token
  // cookie (see backend/app/api/v1/endpoints/auth.py) — without this,
  // /api/v1/auth/refresh never receives the cookie cross-origin (frontend
  // :3000, backend :8000 in dev).
  withCredentials: true,
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
// 5.  Silent refresh on 401 — retried once via the httpOnly refresh cookie
// =============================================================================

/**
 * Concurrent requests that all 401 around the same time (e.g. a dashboard
 * firing several parallel widget calls right as the access token expires)
 * must not each independently call /auth/refresh — that would race
 * multiple refresh-cookie rotations against each other. This coalesces
 * them into one in-flight refresh that every caller awaits.
 */
let _refreshPromise: Promise<string | null> | null = null

async function _refreshAccessToken(): Promise<string | null> {
  if (!_refreshPromise) {
    _refreshPromise = axios
      .post(`${BASE_URL}/api/v1/auth/refresh`, null, { withCredentials: true })
      .then((res) => res.data.access_token as string)
      .catch(() => null)
      .finally(() => {
        _refreshPromise = null
      })
  }
  return _refreshPromise
}

// =============================================================================
// 6.  Response interceptor — silent refresh, then normalise errors
// =============================================================================

apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError<{ error?: string; detail?: unknown }>) => {
    const status = error.response?.status ?? 0
    const originalRequest = error.config as (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined

    const isAuthEndpoint = originalRequest?.url?.includes('/api/v1/auth/login')
      || originalRequest?.url?.includes('/api/v1/auth/refresh')

    if (status === 401 && originalRequest && !originalRequest._retried && !isAuthEndpoint) {
      originalRequest._retried = true
      const newAccessToken = await _refreshAccessToken()
      if (newAccessToken) {
        useAuthStore.getState().setAccessToken(newAccessToken)
        originalRequest.headers = originalRequest.headers ?? {}
        originalRequest.headers['Authorization'] = `Bearer ${newAccessToken}`
        return apiClient(originalRequest)
      }
      // Refresh failed (cookie missing/expired/revoked) — the session is
      // truly over, not just the access token stale. Clear local state so
      // the UI reflects "logged out" instead of silently retrying forever.
      useAuthStore.getState().logout()
    }

    const body = error.response?.data

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
