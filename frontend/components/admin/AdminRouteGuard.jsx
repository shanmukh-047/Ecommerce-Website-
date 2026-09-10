'use client';

import React, { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { Loader2, ShieldAlert } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import Button from '../common/Button';

/**
 * AdminRouteGuard
 * Restricts access exclusively to authenticated staff and administrators.
 */
export default function AdminRouteGuard({ children }) {
  const { isAuthenticated, isStaff, isLoading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace(`/admin-login?next=${encodeURIComponent(pathname)}`);
    }
  }, [isLoading, isAuthenticated, router, pathname]);

  if (isLoading) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3">
        <Loader2 className="h-8 w-8 animate-spin text-saffron-600" />
        <p className="text-xs text-spice-stone font-medium">Verifying administrative security credentials...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  if (!isStaff) {
    return (
      <div className="max-w-md mx-auto my-20 p-8 text-center bg-white rounded-2xl border border-red-200 shadow-subtle">
        <div className="h-12 w-12 rounded-full bg-red-100 text-red-600 flex items-center justify-center mx-auto mb-4">
          <ShieldAlert className="h-6 w-6" />
        </div>
        <h2 className="text-lg font-bold font-display text-spice-black mb-2">Administrative Privileges Required</h2>
        <p className="text-xs text-spice-stone mb-6 leading-relaxed">
          Your account does not possess staff or manager permissions for the Bharat Masala Administration Portal.
        </p>
        <div className="flex items-center justify-center gap-3">
          <Button variant="outline-stone" size="sm" onClick={() => router.push('/')}>
            Back to Store
          </Button>
          <Button
            variant="danger"
            size="sm"
            onClick={async () => {
              await logout();
              router.push('/admin-login');
            }}
          >
            Switch Account
          </Button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
