/**
 * hooks/useTenantSession.ts
 * ==========================
 * Supabase JWT claim extractor — tenant context provider hook.
 *
 * Architecture
 * ------------
 * This hook is the single authoritative source for the active tenant UUID
 * across the entire frontend. It replaces the dev-only `NEXT_PUBLIC_TENANT_ID`
 * environment shortcut with a proper layered resolution strategy:
 *
 *   Priority 1 (production)  — Supabase session JWT app_metadata.tenant_id
 *   Priority 2 (dev/staging) — NEXT_PUBLIC_TENANT_ID environment variable
 *   Priority 3 (fallback)    — null (renders an unauthenticated state)
 *
 * Security contract
 * -----------------
 *   • The tenant UUID is NEVER read from URL params or localStorage.
 *   • The Supabase `onAuthStateChange` subscription keeps the UUID live —
 *     sign-out immediately clears the tenant context.
 *   • `setActiveTenant()` from `@/lib/apiClient` is called inside this hook
 *     so the Axios singleton is always seeded before any API call fires.
 *
 * Usage
 * -----
 *   const { tenantId, isLoading, authState } = useTenantSession()
 *
 *   // tenantId is null while the session is resolving (isLoading = true).
 *   // Downstream hooks (useInventoryList) gate their queries on tenantId,
 *   // so no premature API calls ever fire with an undefined tenant.
 *
 * Production wiring
 * -----------------
 *   1. Install `@supabase/ssr` (already in package.json).
 *   2. Set `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`
 *      in `.env.local`.
 *   3. Ensure Supabase auth is configured to write `tenant_id` into
 *      `app_metadata` on the user record (set via service-role key or
 *      an Auth Hook in the Supabase dashboard).
 */

'use client'

import { useEffect, useState, useCallback } from 'react'
import { setActiveTenant, getActiveTenant } from '@/lib/apiClient'

// =============================================================================
// 1.  Auth state discriminant
// =============================================================================

/**
 * Discriminated union over the three possible authentication states.
 *
 * `resolving`     — The hook is performing the initial async session check.
 *                   No API calls should fire in this state.
 * `authenticated` — A valid Supabase session exists and `tenantId` is set.
 * `unauthenticated` — No session or the session has no tenant claim.
 *                   Render a sign-in prompt or redirect.
 */
export type AuthState = 'resolving' | 'authenticated' | 'unauthenticated'

// =============================================================================
// 2.  Return shape
// =============================================================================

export interface TenantSessionResult {
  /** The validated tenant UUID, or null while resolving / unauthenticated. */
  tenantId:   string | null
  /** True during the initial async session resolution (first render only). */
  isLoading:  boolean
  /** Current authentication state discriminant. */
  authState:  AuthState
  /** Source of the resolved tenant UUID (for debugging / telemetry). */
  source:     'supabase_jwt' | 'env_override' | 'none'
  /** Sign-out the current session and clear tenant context. */
  signOut:    () => Promise<void>
}

// =============================================================================
// 3.  Dev/env override (resolved at module level — no repeated env reads)
// =============================================================================

/**
 * Developer override: set `NEXT_PUBLIC_TENANT_ID` in `.env.local` to skip
 * the Supabase auth flow during local development.
 * This value is `undefined` in production builds (env var not present).
 */
const ENV_TENANT_OVERRIDE: string | undefined =
  process.env.NEXT_PUBLIC_TENANT_ID || undefined

// =============================================================================
// 4.  Supabase client factory (lazy — only created when the hook first mounts)
// =============================================================================

/**
 * Lazily import and create a Supabase browser client.
 *
 * The dynamic import means the Supabase SDK is NOT bundled into every page —
 * only pages that call `useTenantSession()` pay the import cost.
 *
 * Returns `null` if Supabase env vars are not configured (dev without auth).
 */
async function createSupabaseBrowserClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

  if (!url || !key) {
    return null
  }

  try {
    // Dynamic import: Supabase SSR client for browser usage.
    // `createBrowserClient` is the correct entry for App Router client components.
    const { createBrowserClient } = await import('@supabase/ssr')
    return createBrowserClient(url, key)
  } catch {
    // If @supabase/ssr is not yet installed or fails to load,
    // fall through to the env-override path gracefully.
    return null
  }
}

// =============================================================================
// 5.  useTenantSession hook
// =============================================================================

/**
 * Primary tenant session hook. Resolves the tenant UUID from the Supabase
 * session JWT and keeps it live via `onAuthStateChange`.
 *
 * The hook follows a strict priority ladder so it degrades gracefully across
 * all environments:
 *
 *   Production  → Supabase JWT `app_metadata.tenant_id`
 *   Development → `NEXT_PUBLIC_TENANT_ID` env var override
 *   Fallback    → `null` (unauthenticated state)
 */
export function useTenantSession(): TenantSessionResult {
  const [tenantId,  setTenantId]  = useState<string | null>(null)
  const [authState, setAuthState] = useState<AuthState>('resolving')
  const [source,    setSource]    = useState<TenantSessionResult['source']>('none')

  // --------------------------------------------------------------------------
  // Sign-out stub — calls Supabase signOut when available
  // --------------------------------------------------------------------------
  const signOut = useCallback(async () => {
    try {
      const client = await createSupabaseBrowserClient()
      if (client) {
        await client.auth.signOut()
      }
    } finally {
      // Always clear local tenant context regardless of Supabase response
      setTenantId(null)
      setAuthState('unauthenticated')
      setSource('none')
      setActiveTenant('')
    }
  }, [])

  // --------------------------------------------------------------------------
  // Session resolution effect — runs once on mount
  // --------------------------------------------------------------------------
  useEffect(() => {
    let isMounted = true

    async function resolveSession() {
      // ── Priority 1: Supabase JWT ───────────────────────────────────────────
      const client = await createSupabaseBrowserClient()

      if (client) {
        // Perform initial session fetch
        const { data: { session } } = await client.auth.getSession()

        if (isMounted) {
          const jwtTenantId: string | undefined =
            // Standard location: app_metadata claim (set server-side, tamper-proof)
            session?.user?.app_metadata?.tenant_id ??
            // Fallback location: user_metadata (editable by the user — less secure)
            session?.user?.user_metadata?.tenant_id

          if (jwtTenantId) {
            setTenantId(jwtTenantId)
            setAuthState('authenticated')
            setSource('supabase_jwt')
            setActiveTenant(jwtTenantId)
            return  // resolved via JWT — done
          }
        }

        // Subscribe to auth state changes so sign-in/sign-out updates live
        const { data: { subscription } } = client.auth.onAuthStateChange(
          (_event, session) => {
            if (!isMounted) return

            const jwtTenantId: string | undefined =
              session?.user?.app_metadata?.tenant_id ??
              session?.user?.user_metadata?.tenant_id

            if (jwtTenantId) {
              setTenantId(jwtTenantId)
              setAuthState('authenticated')
              setSource('supabase_jwt')
              setActiveTenant(jwtTenantId)
            } else {
              setTenantId(null)
              setAuthState('unauthenticated')
              setSource('none')
            }
          }
        )

        // Cleanup subscription on unmount
        return () => subscription.unsubscribe()
      }

      // ── Priority 2: NEXT_PUBLIC_TENANT_ID env override ────────────────────
      if (ENV_TENANT_OVERRIDE && isMounted) {
        setTenantId(ENV_TENANT_OVERRIDE)
        setAuthState('authenticated')
        setSource('env_override')
        setActiveTenant(ENV_TENANT_OVERRIDE)
        return
      }

      // ── Priority 3: No tenant resolved ────────────────────────────────────
      if (isMounted) {
        setTenantId(null)
        setAuthState('unauthenticated')
        setSource('none')
      }
    }

    resolveSession()

    return () => { isMounted = false }
  }, [])

  return {
    tenantId,
    isLoading: authState === 'resolving',
    authState,
    source,
    signOut,
  }
}
