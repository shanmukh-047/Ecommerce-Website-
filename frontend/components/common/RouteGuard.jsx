'use client';

import React, { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { Loader2, ShieldAlert } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import Button from './Button';

/**
 * RouteGuard component for protecting authenticated routes (Account, Orders, Checkout).
 */
export default function RouteGuard({ children, requireWholesale = false }) {
  const { isAuthenticated, isWholesale, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [isLoading, isAuthenticated, router, pathname]);

  if (isLoading) {
    return (
      <div className="flex min-h-[50vh] flex-col items-center justify-center gap-3">
        <Loader2 className="h-8 w-8 animate-spin text-saffron-600" />
        <p className="text-xs text-spice-stone font-medium">Verifying your secure session...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null; // Will redirect via useEffect
  }

  if (requireWholesale && !isWholesale) {
    return (
      <div className="max-w-md mx-auto my-16 p-8 text-center bg-white rounded-2xl border border-spice-border shadow-subtle">
        <div className="h-12 w-12 rounded-full bg-amber-50 text-amber-600 flex items-center justify-center mx-auto mb-4">
          <ShieldAlert className="h-6 w-6" />
        </div>
        <h2 className="text-lg font-bold font-display text-spice-black mb-2">Wholesale Access Required</h2>
        <p className="text-xs text-spice-stone mb-6">
          This portal is reserved for verified B2B grocers, restaurants, and distributors.
        </p>
        <Button variant="primary" size="md" onClick={() => router.push('/wholesale/register')}>
          Apply for Wholesale Account
        </Button>
      </div>
    );
  }

  return <>{children}</>;
}
