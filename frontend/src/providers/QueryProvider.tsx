/**
 * providers/QueryProvider.tsx
 * ============================
 * TanStack Query v5 client provider — wraps the Next.js App Router tree.
 *
 * Must be a Client Component ('use client') because QueryClientProvider
 * uses React Context, which is not available in Server Components.
 *
 * Wiring: Add <QueryProvider> in `app/layout.tsx` (or the closest shared
 * layout) wrapping {children}.
 */

'use client'

import React, { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

interface QueryProviderProps {
  children: React.ReactNode
}

export function QueryProvider({ children }: QueryProviderProps) {
  /**
   * Stable QueryClient instance per render tree.
   * useState ensures it is created only once per component lifecycle,
   * even in Strict Mode double-render.
   */
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            /**
             * 30 s stale window — data is considered fresh for 30 s after
             * the last successful fetch.  Background refetches only fire
             * once this window has passed.
             */
            staleTime: 30_000,
            /**
             * Retry transient failures up to 3 times with exponential
             * back-off (1 s, 2 s, 4 s).  Capped at 10 s.
             */
            retry: 3,
            retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 10_000),
            /** Refetch when the user returns to the tab / window. */
            refetchOnWindowFocus: true,
          },
          mutations: {
            /** Mutations do not retry automatically by default. */
            retry: 0,
          },
        },
      }),
  )

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}
