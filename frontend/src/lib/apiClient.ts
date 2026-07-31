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

import { useAuthStore, type User } from '@/store/authStore'

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

/** Result of a successful /auth/refresh call — the access token AND the
 * user profile that came with it, so a caller bootstrapping a session from
 * scratch (see authStore.ts's bootstrapAuth, which never has a cached
 * accessToken to start from now that it's memory-only) doesn't need a
 * second round-trip just to learn who's logged in. */
export interface RefreshResult {
  accessToken: string
  user: User
}

/**
 * Concurrent requests that all 401 around the same time (e.g. a dashboard
 * firing several parallel widget calls right as the access token expires)
 * must not each independently call /auth/refresh — that would race
 * multiple refresh-cookie rotations against each other. This coalesces
 * them into one in-flight refresh that every caller awaits.
 *
 * Exported (not module-private) so authStore.ts's bootstrapAuth can reuse
 * the exact same call — and the exact same de-duplication — for the
 * initial silent-refresh-on-app-load flow, instead of re-implementing a
 * second, parallel path to the same endpoint.
 */
let _refreshPromise: Promise<RefreshResult | null> | null = null

export async function refreshAccessToken(): Promise<RefreshResult | null> {
  if (!_refreshPromise) {
    _refreshPromise = axios
      .post(`${BASE_URL}/api/v1/auth/refresh`, null, { withCredentials: true })
      .then((res) => ({ accessToken: res.data.access_token as string, user: res.data.user as User }))
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

    // TenantAuthMiddleware returns this specific 403 (not 401) when the
    // access token carries no tenant_id claim at all — e.g. a token minted
    // before /auth/refresh guaranteed one. It's recoverable the same way a
    // 401 is: a fresh /auth/refresh call either mints a good token or fails
    // cleanly, so route it through the exact same silent-refresh-then-logout
    // path below rather than leaving the caller to render a raw backend
    // error (see: Warehouses/Dashboard/Purchase Orders all showing this
    // verbatim string instead of being bounced to /login).
    const isMissingTenantClaim = status === 403
      && typeof error.response?.data?.detail === 'string'
      && error.response.data.detail.includes('No tenant_id claim found')

    if ((status === 401 || isMissingTenantClaim) && originalRequest && !originalRequest._retried && !isAuthEndpoint) {
      originalRequest._retried = true
      const refreshed = await refreshAccessToken()
      if (refreshed) {
        useAuthStore.getState().setAccessToken(refreshed.accessToken)
        originalRequest.headers = originalRequest.headers ?? {}
        originalRequest.headers['Authorization'] = `Bearer ${refreshed.accessToken}`
        return apiClient(originalRequest)
      }
      // Refresh failed (cookie missing/expired/revoked, or — e.g. after a
      // SECRET_KEY rotation — the refresh token itself no longer verifies
      // either) — the session is truly over, not just the access token
      // stale. Clear local state so the UI reflects "logged out" instead
      // of silently retrying forever.
      useAuthStore.getState().logout()

      // Redirect immediately and unconditionally, rather than relying on
      // AuthGuard's useEffect (subscribed to isAuthenticated) to notice
      // the state change on its next render. That reactive path does
      // still fire, but only after whichever component made this failed
      // call has already re-rendered with a caught error — a dashboard's
      // Promise.all() catch block sets its own error state and paints a
      // broken/zeroed page for one render before the redirect lands. A
      // hard navigation here, fired the moment the session is confirmed
      // dead, pre-empts that: the browser starts leaving the page before
      // any caller's .catch() even finishes running.
      if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
        window.location.href = '/login?reason=session_expired'
      }
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
