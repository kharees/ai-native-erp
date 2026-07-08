'use client';

import Link from 'next/link';
import { useAuthStore } from '@/store/authStore';

export default function LandingPage() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  return (
    <div className="hero">
      <div className="container" style={{ textAlign: 'center' }}>
        <h1>AI Native ERP</h1>
        <p style={{ margin: '0 auto 2rem auto' }}>
          The future of enterprise resource planning. Intelligent, scalable, and built for modern businesses.
        </p>
        <div className="btn-group">
          {isAuthenticated ? (
            <Link href="/dashboard" className="btn btn-primary">
              Go to Dashboard
            </Link>
          ) : (
            <Link href="/login" className="btn btn-primary">
              Sign In
            </Link>
          )}
          <Link href="/inventory" className="btn btn-secondary">
            View Inventory
          </Link>
        </div>
      </div>
    </div>
  );
}
