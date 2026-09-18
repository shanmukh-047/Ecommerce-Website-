'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { Mail, CheckCircle2, AlertCircle, ArrowRight } from 'lucide-react';
import authService from '../../services/authService';
import Button from '../../components/common/Button';
import Input from '../../components/common/Input';
import Card from '../../components/common/Card';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!email.trim()) {
      setError('Please enter your email address');
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      setError('Enter a valid email address');
      return;
    }

    setIsLoading(true);
    try {
      await authService.requestPasswordReset(email.trim().toLowerCase());
      setIsSubmitted(true);
    } catch (err) {
      setError(err.userMessage || err.message || 'Failed to request password reset. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-6">
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
            Reset Your Password
          </h1>
          <p className="text-xs text-spice-stone mt-1">
            Enter your registered email to receive recovery instructions
          </p>
        </div>

        <Card variant="elevated" padding="lg" className="rounded-2xl">
          {isSubmitted ? (
            <div className="space-y-4">
              <div className="rounded-xl border border-emerald-200 bg-emerald-50/80 p-4 text-xs text-emerald-800 flex items-start gap-3">
                <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-600 mt-0.5" />
                <div>
                  <p className="font-semibold mb-1">Reset Request Received</p>
                  <p className="text-emerald-700 leading-relaxed">
                    If an account exists with <span className="font-medium">{email}</span>, password reset instructions have been dispatched. Please check your inbox and spam folder.
                  </p>
                </div>
              </div>
              <Link href="/login" className="block w-full">
                <Button variant="outline" size="md" isFullWidth className="text-xs font-semibold">
                  Return to Sign In
                </Button>
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div
                  role="alert"
                  className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50/80 p-3 text-xs text-red-700"
                >
                  <AlertCircle className="h-4 w-4 shrink-0 text-red-600 mt-0.5" />
                  <div className="flex-1 font-medium">{error}</div>
                </div>
              )}

              <Input
                label="Registered Email Address"
                type="email"
                required
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (error) setError('');
                }}
                leftIcon={<Mail className="h-4 w-4" />}
                placeholder="name@example.com"
              />

              <Button
                type="submit"
                variant="primary"
                size="lg"
                isFullWidth
                isLoading={isLoading}
                className="font-semibold uppercase tracking-wider text-xs"
              >
                Send Reset Instructions
              </Button>

              <div className="text-center pt-2">
                <Link
                  href="/login"
                  className="text-xs font-medium text-spice-stone hover:text-spice-black hover:underline"
                >
                  &larr; Back to Sign In
                </Link>
              </div>
            </form>
          )}
        </Card>
      </div>
    </div>
  );
}
