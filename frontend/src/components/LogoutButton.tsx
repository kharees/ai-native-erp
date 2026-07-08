'use client';

import { useAuthStore } from '@/store/authStore';
import { useRouter } from 'next/navigation';
import axios from 'axios';

export default function LogoutButton() {
  const logout = useAuthStore((state) => state.logout);
  const router = useRouter();

  const handleLogout = async () => {
    try {
      await axios.post('http://localhost:8000/api/v1/auth/logout');
    } catch (e) {
      // Ignore errors on logout
    } finally {
      logout();
      delete axios.defaults.headers.common['Authorization'];
      delete axios.defaults.headers.common['X-Tenant-ID'];
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
