'use client';

import React, { useState, Suspense } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Eye, EyeOff, Lock, Mail, ArrowRight, ShieldCheck, AlertCircle, CheckCircle2 } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../components/common/Toast';
import Button from '../../components/common/Button';
import Input from '../../components/common/Input';
import Card from '../../components/common/Card';
import authService from '../../services/authService';

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextUrl = searchParams.get('next') || '/account';

  const { login, isAuthenticated } = useAuth();
  const { success } = useToast();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState({});
  const [apiError, setApiError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Forgot password state
  const [showForgot, setShowForgot] = useState(false);
  const [forgotEmail, setForgotEmail] = useState('');
  const [forgotSubmitted, setForgotSubmitted] = useState(false);
  const [forgotLoading, setForgotLoading] = useState(false);
  const [forgotError, setForgotError] = useState('');

  // If already authenticated, redirect
  React.useEffect(() => {
    if (isAuthenticated) {
      router.replace(nextUrl);
    }
  }, [isAuthenticated, router, nextUrl]);

  const validate = () => {
    const errs = {};
    if (!email.trim()) {
      errs.email = 'Email address is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      errs.email = 'Enter a valid email address';
    }

    if (!password) {
      errs.password = 'Password is required';
    } else if (password.length < 8) {
      errs.password = 'Password must be at least 8 characters';
    }

    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setApiError('');

    if (!validate()) return;

    setIsSubmitting(true);
    try {
      const result = await login(email.trim().toLowerCase(), password);
      const userName = result?.user?.first_name || result?.user?.full_name || 'Customer';
      success(`Welcome back, ${userName}!`, 'Signed In');
      router.replace(nextUrl);
    } catch (err) {
      setApiError(err.userMessage || err.message || 'Invalid email or password. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleForgotSubmit = async (e) => {
    e.preventDefault();
    setForgotError('');
    if (!forgotEmail.trim()) {
      setForgotError('Please enter your email address');
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(forgotEmail.trim())) {
      setForgotError('Enter a valid email address');
      return;
    }

    setForgotLoading(true);
    try {
      await authService.requestPasswordReset(forgotEmail.trim().toLowerCase());
      setForgotSubmitted(true);
    } catch (err) {
      setForgotError(err.userMessage || err.message || 'Failed to request password reset. Please try again.');
    } finally {
      setForgotLoading(false);
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-6">
        {/* Brand Header */}
        <div className="text-center">
          <Link
            href="/"
            className="inline-flex items-center gap-2 font-display text-2xl font-bold tracking-tight text-spice-black mb-2"
          >
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-saffron-600 text-white font-serif text-base shadow-2xs">
              B
            </span>
            <span>
              BHARAT <span className="text-saffron-600 font-normal italic">MASALA</span>
            </span>
          </Link>
          <h1 className="text-xl font-bold font-display text-spice-black mt-2">
            {showForgot ? 'Reset Your Password' : 'Sign In to Your Account'}
          </h1>
          <p className="text-xs text-spice-stone mt-1">
            {showForgot
              ? 'Enter your registered email to receive recovery instructions'
              : 'Access your order tracking, wholesale pricing, and saved addresses'}
          </p>
        </div>

        {/* Form Container */}
        <Card variant="elevated" padding="lg" className="rounded-2xl">
          {showForgot ? (
            <div className="space-y-4">
              {forgotSubmitted ? (
                <div className="space-y-4">
                  <div className="rounded-xl border border-emerald-200 bg-emerald-50/80 p-4 text-xs text-emerald-800 flex items-start gap-3">
                    <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-600 mt-0.5" />
                    <div>
                      <p className="font-semibold mb-1">Reset Request Received</p>
                      <p className="text-emerald-700 leading-relaxed">
                        If an account exists with <span className="font-medium">{forgotEmail}</span>, password reset instructions have been dispatched. Please check your inbox and spam folder.
                      </p>
                    </div>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="md"
                    isFullWidth
                    onClick={() => {
                      setShowForgot(false);
                      setForgotSubmitted(false);
                    }}
                    className="text-xs font-semibold"
                  >
                    Return to Sign In
                  </Button>
                </div>
              ) : (
                <form onSubmit={handleForgotSubmit} className="space-y-4">
                  {forgotError && (
                    <div
                      role="alert"
                      className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50/80 p-3 text-xs text-red-700"
                    >
                      <AlertCircle className="h-4 w-4 shrink-0 text-red-600 mt-0.5" />
                      <div className="flex-1 font-medium">{forgotError}</div>
                    </div>
                  )}

                  <Input
                    label="Registered Email Address"
                    type="email"
                    required
                    value={forgotEmail}
                    onChange={(e) => {
                      setForgotEmail(e.target.value);
                      if (forgotError) setForgotError('');
                    }}
                    leftIcon={<Mail className="h-4 w-4" />}
                    placeholder="name@example.com"
                  />

                  <Button
                    type="submit"
                    variant="primary"
                    size="lg"
                    isFullWidth
                    isLoading={forgotLoading}
                    className="font-semibold uppercase tracking-wider text-xs"
                  >
                    Send Reset Instructions
                  </Button>

                  <div className="text-center pt-2">
                    <button
                      type="button"
                      onClick={() => setShowForgot(false)}
                      className="text-xs font-medium text-spice-stone hover:text-spice-black hover:underline"
                    >
                      &larr; Back to Sign In
                    </button>
                  </div>
                </form>
              )}
            </div>
          ) : (
            <>
              {apiError && (
                <div
                  role="alert"
                  className="mb-5 flex items-start gap-3 rounded-xl border border-red-200 bg-red-50/80 p-3 text-xs text-red-700 animate-slideUp"
                >
                  <AlertCircle className="h-4 w-4 shrink-0 text-red-600 mt-0.5" />
                  <div className="flex-1 font-medium">{apiError}</div>
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                <Input
                  label="Email Address"
                  type="email"
                  name="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    if (errors.email) setErrors((prev) => ({ ...prev, email: '' }));
                  }}
                  error={errors.email}
                  leftIcon={<Mail className="h-4 w-4" />}
                  placeholder="name@example.com"
                />

                <div>
                  <Input
                    label="Password"
                    type={showPassword ? 'text' : 'password'}
                    name="password"
                    autoComplete="current-password"
                    required
                    value={password}
                    onChange={(e) => {
                      setPassword(e.target.value);
                      if (errors.password) setErrors((prev) => ({ ...prev, password: '' }));
                    }}
                    error={errors.password}
                    leftIcon={<Lock className="h-4 w-4" />}
                    rightIcon={
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="text-spice-stone hover:text-spice-black focus:outline-none"
                        aria-label={showPassword ? 'Hide password' : 'Show password'}
                      >
                        {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    }
                    placeholder="••••••••"
                  />
                  <div className="flex justify-end mt-1.5">
                    <button
                      type="button"
                      onClick={() => {
                        setForgotEmail(email);
                        setForgotError('');
                        setForgotSubmitted(false);
                        setShowForgot(true);
                      }}
                      className="text-xs font-medium text-saffron-700 hover:text-saffron-800 hover:underline"
                    >
                      Forgot password?
                    </button>
                  </div>
                </div>

                <div className="pt-2">
                  <Button
                    type="submit"
                    variant="primary"
                    size="lg"
                    isFullWidth
                    isLoading={isSubmitting}
                    rightIcon={<ArrowRight className="h-4 w-4" />}
                    className="font-semibold uppercase tracking-wider text-xs"
                  >
                    Sign In
                  </Button>
                </div>
              </form>
            </>
          )}

          {/* Registration Links */}
          <div className="mt-6 pt-5 border-t border-spice-borderSubtle text-center text-xs space-y-3">
            <p className="text-spice-stone">
              Don&apos;t have an account yet?{' '}
              <Link
                href={`/register${nextUrl !== '/account' ? `?next=${encodeURIComponent(nextUrl)}` : ''}`}
                className="font-semibold text-saffron-700 hover:text-saffron-800 hover:underline"
              >
                Create an Account
              </Link>
            </p>

            <div className="rounded-xl bg-spice-canvas/80 border border-spice-borderSubtle p-3 text-left">
              <div className="flex items-center gap-2 text-xs font-semibold text-spice-black mb-1">
                <ShieldCheck className="h-4 w-4 text-cardamom-700" />
                <span>Wholesale &amp; Bulk Procurement</span>
              </div>
              <p className="text-[11px] text-spice-stone leading-relaxed">
                Grocery retailers, restaurants, and distributors qualify for wholesale tier pricing with GST input tax credit.
              </p>
              <Link
                href="/register?tab=wholesale"
                className="inline-block mt-2 text-xs font-semibold text-cardamom-800 hover:text-cardamom-900 hover:underline"
              >
                Apply for B2B Wholesale Account &rarr;
              </Link>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-[80vh] flex items-center justify-center">
          <div className="h-8 w-8 rounded-full border-2 border-saffron-600 border-t-transparent animate-spin" />
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
