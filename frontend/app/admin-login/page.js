'use client';

import React, { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { ShieldCheck, Lock, Mail, ArrowRight, AlertCircle, Loader2 } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import Button from '../../components/common/Button';

function AdminLoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextUrl = searchParams.get('next') || '/admin-dashboard';
  const { user, login, isAuthenticated, isStaff, isLoading: isAuthLoading } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [view, setView] = useState('login'); // 'login' | 'forgot'
  const [forgotEmail, setForgotEmail] = useState('');
  const [forgotSuccess, setForgotSuccess] = useState(false);
  const [forgotError, setForgotError] = useState('');
  const [isSubmittingForgot, setIsSubmittingForgot] = useState(false);

  // If already logged in as staff, redirect immediately
  useEffect(() => {
    if (!isAuthLoading && isAuthenticated) {
      if (isStaff) {
        router.replace(nextUrl);
      } else {
        setErrorMessage('Your account is logged in but lacks staff permissions.');
      }
    }
  }, [isAuthLoading, isAuthenticated, isStaff, router, nextUrl]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');
    setIsSubmitting(true);

    try {
      const data = await login(email.trim(), password);
      const loggedUser = data?.user;
      const isStaffUser =
        loggedUser?.is_staff ||
        loggedUser?.is_superuser ||
        loggedUser?.role === 'STAFF' ||
        loggedUser?.role === 'MANAGER' ||
        loggedUser?.role === 'ADMIN';

      if (!isStaffUser) {
        setErrorMessage('Access Denied: This portal is restricted to staff and managers.');
        return;
      }

      router.replace(nextUrl);
    } catch (err) {
      console.error('Admin login error:', err);
      const msg = err?.message || 'Invalid staff credentials. Please check your email and password.';
      setErrorMessage(msg.includes('Invalid credentials') ? 'Invalid email or password.' : msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleForgotSubmit = async (e) => {
    e.preventDefault();
    setForgotError('');
    if (!forgotEmail.trim()) {
      setForgotError('Please enter your staff email address.');
      return;
    }
    setIsSubmittingForgot(true);
    try {
      const authService = (await import('../../services/authService')).default;
      await authService.requestPasswordReset(forgotEmail.trim().toLowerCase());
      setForgotSuccess(true);
    } catch (err) {
      setForgotError(err.userMessage || err.message || 'Failed to dispatch reset email. Please try again.');
    } finally {
      setIsSubmittingForgot(false);
    }
  };

  return (
    <div className="min-h-screen bg-spice-earth flex flex-col justify-center py-12 sm:px-6 lg:px-8 font-body">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="w-14 h-14 rounded-2xl bg-saffron-600 text-white flex items-center justify-center mx-auto shadow-saffron-glow mb-4">
          <ShieldCheck className="h-8 w-8" />
        </div>
        <h1 className="text-2xl font-black font-display text-white tracking-wide">
          BHARAT MASALA
        </h1>
        <p className="mt-1 text-xs uppercase font-bold tracking-widest text-saffron-400">
          Staff &amp; Operations Portal
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4">
        <div className="bg-white py-8 px-6 sm:px-10 rounded-2xl shadow-xl border border-stone-700/30">
          {view === 'login' ? (
            <form onSubmit={handleSubmit} className="space-y-4">
              {errorMessage && (
                <div className="p-3.5 rounded-xl bg-red-50 border border-red-200 text-xs text-red-800 flex items-start gap-2.5">
                  <AlertCircle className="h-4 w-4 text-red-600 shrink-0 mt-0.5" />
                  <span className="leading-relaxed">{errorMessage}</span>
                </div>
              )}

              <div>
                <label htmlFor="staff-email" className="block text-xs font-bold text-spice-black mb-1">
                  Staff Email Address
                </label>
                <div className="relative">
                  <Mail className="h-4 w-4 text-stone-400 absolute left-3 top-3" />
                  <input
                    id="staff-email"
                    type="email"
                    required
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="admin@bharatmasala.com"
                    className="w-full pl-9 pr-3 py-2.5 rounded-xl border border-stone-300 text-xs text-spice-black placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-saffron-500 font-medium"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label htmlFor="staff-password" className="block text-xs font-bold text-spice-black">
                    Password
                  </label>
                  <button
                    type="button"
                    onClick={() => {
                      setView('forgot');
                      setForgotEmail(email);
                      setForgotError('');
                      setForgotSuccess(false);
                    }}
                    className="text-xs font-semibold text-saffron-600 hover:text-saffron-700 transition-colors"
                  >
                    Forgot Password?
                  </button>
                </div>
                <div className="relative">
                  <Lock className="h-4 w-4 text-stone-400 absolute left-3 top-3" />
                  <input
                    id="staff-password"
                    type="password"
                    required
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full pl-9 pr-3 py-2.5 rounded-xl border border-stone-300 text-xs text-spice-black placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-saffron-500 font-medium"
                  />
                </div>
              </div>

              <Button
                type="submit"
                variant="primary"
                size="md"
                isFullWidth
                isLoading={isSubmitting}
                rightIcon={<ArrowRight className="h-4 w-4" />}
                className="mt-2"
              >
                Sign In to Admin Deck
              </Button>
            </form>
          ) : (
            <div className="space-y-4">
              <div className="text-center pb-2">
                <h2 className="text-base font-bold text-spice-black">Staff Password Recovery</h2>
                <p className="text-xs text-stone-500 mt-1">
                  Enter your registered staff email address to receive reset instructions.
                </p>
              </div>

              {forgotSuccess ? (
                <div className="p-4 rounded-xl bg-green-50 border border-green-200 text-xs text-green-800 space-y-2">
                  <p className="font-semibold">Reset instructions dispatched!</p>
                  <p>
                    If an account matching <span className="font-bold">{forgotEmail}</span> is on file, a 1-hour secure password reset link has been dispatched.
                  </p>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    isFullWidth
                    onClick={() => {
                      setView('login');
                      setForgotSuccess(false);
                    }}
                    className="mt-3"
                  >
                    Back to Admin Sign In
                  </Button>
                </div>
              ) : (
                <form onSubmit={handleForgotSubmit} className="space-y-4">
                  {forgotError && (
                    <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-xs text-red-800 flex items-start gap-2">
                      <AlertCircle className="h-4 w-4 text-red-600 shrink-0 mt-0.5" />
                      <span>{forgotError}</span>
                    </div>
                  )}

                  <div>
                    <label htmlFor="recovery-email" className="block text-xs font-bold text-spice-black mb-1">
                      Staff Email Address
                    </label>
                    <div className="relative">
                      <Mail className="h-4 w-4 text-stone-400 absolute left-3 top-3" />
                      <input
                        id="recovery-email"
                        type="email"
                        required
                        autoComplete="email"
                        value={forgotEmail}
                        onChange={(e) => setForgotEmail(e.target.value)}
                        placeholder="admin@bharatmasala.com"
                        className="w-full pl-9 pr-3 py-2.5 rounded-xl border border-stone-300 text-xs text-spice-black placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-saffron-500 font-medium"
                      />
                    </div>
                  </div>

                  <Button
                    type="submit"
                    variant="primary"
                    size="md"
                    isFullWidth
                    isLoading={isSubmittingForgot}
                    rightIcon={<ArrowRight className="h-4 w-4" />}
                  >
                    Send Recovery Email
                  </Button>

                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    isFullWidth
                    onClick={() => {
                      setView('login');
                      setForgotError('');
                    }}
                    className="text-stone-500 text-xs"
                  >
                    Cancel
                  </Button>
                </form>
              )}
            </div>
          )}

          <div className="mt-6 pt-6 border-t border-stone-200 text-center">
            <Link
              href="/"
              className="text-xs text-stone-500 hover:text-spice-black font-semibold transition-colors"
            >
              &larr; Return to Customer Storefront
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function AdminLoginPage() {
  return (
    <React.Suspense
      fallback={
        <div className="min-h-screen bg-spice-earth flex items-center justify-center">
          <div className="h-8 w-8 rounded-full border-2 border-saffron-500 border-t-transparent animate-spin" />
        </div>
      }
    >
      <AdminLoginForm />
    </React.Suspense>
  );
}
