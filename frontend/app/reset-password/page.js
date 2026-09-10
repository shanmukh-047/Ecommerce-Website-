'use client';

import React, { useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Lock, Eye, EyeOff, CheckCircle2, AlertCircle, ArrowRight, ShieldCheck } from 'lucide-react';
import authService from '../../services/authService';
import Button from '../../components/common/Button';
import Input from '../../components/common/Input';
import Card from '../../components/common/Card';

function ResetPasswordForm() {
  const searchParams = useSearchParams();

  // Support both 'uid' and 'uidb64' param names
  const uid = searchParams.get('uid') || searchParams.get('uidb64') || '';
  const token = searchParams.get('token') || '';

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [errors, setErrors] = useState({});
  const [apiError, setApiError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  // Missing token or uid state
  if (!uid || !token) {
    return (
      <div className="w-full max-w-md mx-auto">
        <Card variant="elevated" padding="lg" className="rounded-3xl border border-spice-border shadow-card text-center space-y-4">
          <div className="w-12 h-12 rounded-2xl bg-amber-50 border border-amber-200 text-amber-600 flex items-center justify-center mx-auto">
            <AlertCircle className="h-6 w-6" />
          </div>
          <h1 className="text-xl font-bold font-display text-spice-black">
            Invalid Reset Link
          </h1>
          <p className="text-xs text-spice-stone leading-relaxed">
            This password reset link is incomplete or missing necessary authorization credentials.
            Please request a new reset link from the login page.
          </p>
          <div className="pt-2 flex flex-col gap-2">
            <Link href="/" className="w-full">
              <Button variant="primary" size="md" isFullWidth className="text-xs font-semibold">
                Go to Storefront Login
              </Button>
            </Link>
            <Link href="/admin-login" className="w-full">
              <Button variant="outline" size="sm" isFullWidth className="text-xs text-spice-stone">
                Go to Admin Staff Login
              </Button>
            </Link>
          </div>
        </Card>
      </div>
    );
  }

  const validate = () => {
    const errs = {};
    if (!password) {
      errs.password = 'Password is required.';
    } else if (password.length < 8) {
      errs.password = 'Password must be at least 8 characters long.';
    }

    if (!confirmPassword) {
      errs.confirmPassword = 'Confirmation password is required.';
    } else if (password !== confirmPassword) {
      errs.confirmPassword = 'Passwords do not match.';
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
      await authService.confirmPasswordReset({
        uid,
        token,
        new_password: password,
        confirm_password: confirmPassword,
      });
      setIsSuccess(true);
    } catch (err) {
      console.error('Password reset confirm error:', err);
      if (err.isNetworkError || err.status === 0) {
        setApiError('Unable to connect to the backend server. Please verify your connection.');
      } else if (err.details && typeof err.details === 'object') {
        const fieldErrors = {};
        for (const [key, val] of Object.entries(err.details)) {
          const msg = Array.isArray(val) ? val.join(' ') : String(val);
          if (key === 'new_password') fieldErrors.password = msg;
          else if (key === 'confirm_password') fieldErrors.confirmPassword = msg;
          else if (key === 'token' || key === 'uid' || key === 'error') {
            setApiError(msg);
          }
        }
        if (Object.keys(fieldErrors).length > 0) {
          setErrors(fieldErrors);
        }
        if (!apiError && Object.keys(fieldErrors).length === 0) {
          setApiError(err.userMessage || err.message || 'Password reset failed. Please request a new link.');
        }
      } else {
        setApiError(err.userMessage || err.message || 'Password reset failed. This link may have expired.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="w-full max-w-md mx-auto space-y-6">
      {/* Brand Header */}
      <div className="text-center space-y-2">
        <div className="inline-flex items-center gap-2 font-display text-2xl font-bold tracking-tight text-spice-black">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-saffron-500 to-saffron-700 text-white font-serif text-lg shadow-saffron-glow">
            B
          </span>
          <span>
            BHARAT <span className="text-saffron-600 font-normal italic">MASALA</span>
          </span>
        </div>

        <h1 className="text-xl sm:text-2xl font-bold font-display text-spice-black">
          {isSuccess ? 'Password Reset Successful' : 'Create New Password'}
        </h1>
        <p className="text-xs text-spice-stone max-w-sm mx-auto">
          {isSuccess
            ? 'Your credentials have been securely updated. You may now sign in.'
            : 'Enter a strong new password with a minimum of 8 characters.'}
        </p>
      </div>

      <Card variant="elevated" padding="lg" className="rounded-3xl border border-spice-border shadow-card">
        {isSuccess ? (
          <div className="py-4 text-center space-y-4 animate-slideUp">
            <div className="w-14 h-14 bg-cardamom-50 border border-cardamom-200 rounded-full flex items-center justify-center mx-auto text-cardamom-700">
              <CheckCircle2 className="h-8 w-8" />
            </div>

            <div className="space-y-1">
              <h2 className="text-base font-bold text-spice-black">Account Successfully Recovered</h2>
              <p className="text-xs text-spice-stone leading-relaxed">
                Your new password is now active. All previous reset tokens and credentials have been retired.
              </p>
            </div>

            <div className="pt-2 flex flex-col gap-2">
              <Link href="/" className="w-full">
                <Button
                  variant="primary"
                  size="md"
                  isFullWidth
                  rightIcon={<ArrowRight className="h-4 w-4" />}
                  className="text-xs font-semibold shadow-saffron-glow"
                >
                  Sign In to Storefront
                </Button>
              </Link>
              <Link href="/admin-login" className="w-full">
                <Button
                  variant="ghost"
                  size="sm"
                  isFullWidth
                  className="text-xs text-spice-stone hover:text-spice-black"
                >
                  Sign In to Admin Deck
                </Button>
              </Link>
            </div>
          </div>
        ) : (
          <form noValidate onSubmit={handleSubmit} className="space-y-4">
            {apiError && (
              <div
                role="alert"
                className="flex items-start gap-2.5 rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-700 animate-slideUp"
              >
                <AlertCircle className="h-4 w-4 shrink-0 text-red-600 mt-0.5" />
                <div className="flex-1 font-medium leading-relaxed">
                  {apiError}
                  {apiError.toLowerCase().includes('expired') || apiError.toLowerCase().includes('invalid') ? (
                    <div className="mt-2">
                      <Link href="/" className="font-bold underline text-red-800 hover:text-red-900">
                        Request a new reset link &rarr;
                      </Link>
                    </div>
                  ) : null}
                </div>
              </div>
            )}

            <div>
              <Input
                label="New Password"
                type={showPassword ? 'text' : 'password'}
                name="new_password"
                autoComplete="new-password"
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
                placeholder="Minimum 8 characters"
              />
              <p className="mt-1 text-[11px] text-spice-stone">
                Must be at least 8 characters long and not entirely numeric.
              </p>
            </div>

            <div>
              <Input
                label="Confirm New Password"
                type={showConfirmPassword ? 'text' : 'password'}
                name="confirm_password"
                autoComplete="new-password"
                required
                value={confirmPassword}
                onChange={(e) => {
                  setConfirmPassword(e.target.value);
                  if (errors.confirmPassword) setErrors((prev) => ({ ...prev, confirmPassword: '' }));
                }}
                error={errors.confirmPassword}
                leftIcon={<Lock className="h-4 w-4" />}
                rightIcon={
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="text-spice-stone hover:text-spice-black focus:outline-none"
                    aria-label={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
                  >
                    {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                }
                placeholder="Re-enter your new password"
              />
            </div>

            <div className="pt-2">
              <Button
                type="submit"
                variant="primary"
                size="lg"
                isFullWidth
                isLoading={isSubmitting}
                rightIcon={<ArrowRight className="h-4 w-4" />}
                className="font-semibold uppercase tracking-wider text-xs shadow-saffron-glow"
              >
                Update Password
              </Button>
            </div>
          </form>
        )}

        <div className="mt-6 pt-5 border-t border-spice-borderSubtle text-center text-xs space-y-2">
          <div className="flex items-center justify-center gap-1 text-[11px] text-spice-stone">
            <ShieldCheck className="h-3.5 w-3.5 text-cardamom-700" />
            <span>Encrypted with PBKDF2-SHA256 &middot; 256-Bit SSL</span>
          </div>
        </div>
      </Card>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="min-h-screen bg-[#FAF8F5] flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8 relative overflow-hidden">
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-96 bg-gradient-to-b from-saffron-500/10 via-amber-200/5 to-transparent pointer-events-none rounded-b-[4rem]" />
      <div className="relative z-10">
        <Suspense
          fallback={
            <div className="w-full max-w-md mx-auto text-center py-12">
              <div className="h-8 w-8 mx-auto rounded-full border-2 border-saffron-500 border-t-transparent animate-spin" />
            </div>
          }
        >
          <ResetPasswordForm />
        </Suspense>
      </div>
    </div>
  );
}
