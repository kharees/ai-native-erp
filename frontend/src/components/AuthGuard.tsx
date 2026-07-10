'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, hasHydrated } = useAuthStore();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    // Wait for the persisted session to finish loading from localStorage before
    // deciding to redirect - otherwise every hard reload of a valid session
    // bounces the user to /login during the one render tick before hydration
    // completes.
    if (hasHydrated && !isAuthenticated) {
      router.push('/login');
    }
  }, [hasHydrated, isAuthenticated, router, pathname]);

  if (!hasHydrated || !isAuthenticated) {
    return null; // Return nothing or a spinner while hydrating/redirecting
  }

  return <>{children}</>;
}
