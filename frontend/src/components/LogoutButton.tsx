'use client';

import { useAuthStore } from '@/store/authStore';
import { useRouter } from 'next/navigation';
import apiClient from '@/lib/apiClient';

export default function LogoutButton() {
  const logout = useAuthStore((state) => state.logout);
  const router = useRouter();

  const handleLogout = async () => {
    try {
      await apiClient.post('/api/v1/auth/logout');
    } catch {
      // Ignore errors on logout — always clear local state
    } finally {
      logout();
      router.push('/login');
    }
  };

  return (
    <button 
      onClick={handleLogout}
      className="btn btn-secondary"
      style={{ marginLeft: '1rem', padding: '0.5rem 1rem' }}
    >
      Logout
    </button>
  );
}
