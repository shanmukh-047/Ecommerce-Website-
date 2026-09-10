'use client';

import React, { useState, useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { useAuth } from '../../context/AuthContext';
import BrandIntro from '../intro/BrandIntro';
import StorefrontAuth from '../auth/StorefrontAuth';

/**
 * StorefrontAccessGate
 * 
 * Enforces the requested initial user flow:
 * 1. Unauthenticated First Visit: ~10-second animated Bharat Masala intro
 * 2. After Intro: Authentication screen (Login / Register)
 * 3. After Successful Authentication: Full Bharat Masala e-commerce website
 * 
 * Safeguards:
 * - Admin routes (/admin-login, /admin-dashboard, /admin/*) always bypass the gate.
 * - Authenticated visitors immediately see the full e-commerce website without replay.
 * - Intro completion is recorded in sessionStorage so it only plays once per session.
 * - Deterministic timer, zero hydration mismatch, zero memory leaks.
 */
export default function StorefrontAccessGate({ children }) {
  const pathname = usePathname() || '/';
  const { isAuthenticated, isLoading: isAuthLoading } = useAuth();

  const [isMounted, setIsMounted] = useState(false);
  const [introCompleted, setIntroCompleted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
    try {
      const seen = sessionStorage.getItem('bharat_intro_completed');
      if (seen === 'true') {
        setIntroCompleted(true);
      }
    } catch {
      // In private browsing mode where sessionStorage might throw
      setIntroCompleted(false);
    }
  }, []);

  // Admin routes must never be blocked by customer storefront gate
  const isAdminRoute =
    pathname.startsWith('/admin') ||
    pathname.startsWith('/admin-login') ||
    pathname.startsWith('/admin-dashboard');

  if (isAdminRoute) {
    return <>{children}</>;
  }

  // Before hydration, render children cleanly to prevent hydration mismatches
  if (!isMounted) {
    return (
      <div className="min-h-screen bg-spice-canvas flex items-center justify-center">
        <div className="h-8 w-8 rounded-full border-2 border-saffron-600 border-t-transparent animate-spin" />
      </div>
    );
  }

  // If user is authenticated, unlock the complete e-commerce website immediately!
  if (isAuthenticated) {
    return <>{children}</>;
  }

  // If unauthenticated and hasn't seen the intro this session, play the 10-second intro
  if (!introCompleted) {
    return (
      <BrandIntro
        onComplete={() => {
          try {
            sessionStorage.setItem('bharat_intro_completed', 'true');
          } catch {}
          setIntroCompleted(true);
        }}
      />
    );
  }

  // If unauthenticated and intro is complete, show the polished authentication screen
  return (
    <StorefrontAuth
      onSuccess={() => {
        // useAuth() will update isAuthenticated to true, which immediately renders children
      }}
    />
  );
}
