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
  refreshToken: string | null;
  isAuthenticated: boolean;
  hasHydrated: boolean;
  setAuth: (user: User, accessToken: string, refreshToken: string) => void;
  logout: () => void;
  setHasHydrated: (value: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      // Zustand's persist middleware rehydrates from localStorage asynchronously
      // after the initial (unauthenticated) state renders. Consumers that decide
      // whether to redirect to /login (e.g. AuthGuard) must wait for hasHydrated
      // before trusting isAuthenticated, or every hard reload of a logged-in
      // session bounces the user out before the persisted token loads.
      hasHydrated: false,
      setAuth: (user, accessToken, refreshToken) =>
        set({ user, accessToken, refreshToken, isAuthenticated: true }),
      logout: () => set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false }),
      setHasHydrated: (value) => set({ hasHydrated: value }),
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => (typeof window !== 'undefined' ? localStorage : undefined!)),
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);
