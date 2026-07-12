import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

export interface User {
  id: string;
  email: string;
  tenant_id: string | null;
  full_name: string | null;
}

export interface AuthState {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  hasHydrated: boolean;
  setAuth: (user: User, accessToken: string) => void;
  /** Updates just the access token — used by apiClient's silent-refresh-on-401
   * interceptor, which has a fresh token but no reason to touch `user`. */
  setAccessToken: (accessToken: string) => void;
  logout: () => void;
  setHasHydrated: (value: boolean) => void;
}

// The refresh token is never held here — it lives only in the httpOnly
// `refresh_token` cookie the backend sets on /login and /refresh (see
// backend/app/api/v1/endpoints/auth.py), which JS cannot read. Previously
// this store persisted BOTH tokens to localStorage; any XSS anywhere in the
// app could read them straight out of localStorage and exfiltrate a
// long-lived refresh token, not just the short-lived access token.
//
// The access token itself still persists to localStorage for now (not
// fully memory-only) — moving it out entirely means bootstrapping a fresh
// access token via a silent /refresh call on every app load before
// rendering protected content, which is a real change to the auth
// bootstrap flow (session hydration was already a hard-won fix — see
// hasHydrated below) that deserves its own pass rather than being bundled
// into the cookie fix. The httpOnly cookie change is the higher-value,
// lower-risk half of this fix: the refresh token (long-lived, the more
// damaging thing to leak) is what actually moved off localStorage.
export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      // Zustand's persist middleware rehydrates from localStorage asynchronously
      // after the initial (unauthenticated) state renders. Consumers that decide
      // whether to redirect to /login (e.g. AuthGuard) must wait for hasHydrated
      // before trusting isAuthenticated, or every hard reload of a logged-in
      // session bounces the user out before the persisted token loads.
      hasHydrated: false,
      setAuth: (user, accessToken) =>
        set({ user, accessToken, isAuthenticated: true }),
      setAccessToken: (accessToken) => set({ accessToken }),
      logout: () => set({ user: null, accessToken: null, isAuthenticated: false }),
      setHasHydrated: (value) => set({ hasHydrated: value }),
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => (typeof window !== 'undefined' ? localStorage : undefined!)),
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);
