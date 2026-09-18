'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../../context/AuthContext';
import { Loader2 } from 'lucide-react';

export default function AdminPage() {
  const router = useRouter();
  const { isAuthenticated, isStaff, isLoading } = useAuth();

  useEffect(() => {
    if (!isLoading) {
      if (isAuthenticated && isStaff) {
        router.replace('/admin-dashboard');
      } else {
        router.replace('/admin-login');
      }
    }
  }, [isLoading, isAuthenticated, isStaff, router]);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3">
      <Loader2 className="h-8 w-8 animate-spin text-saffron-600" />
      <p className="text-xs text-spice-stone font-medium">Redirecting to Admin Portal...</p>
    </div>
  );
}
