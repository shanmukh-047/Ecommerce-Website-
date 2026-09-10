'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { Eye, EyeOff, Lock, Mail, ArrowRight, ShieldCheck, AlertCircle, Sparkles, User, Phone, CheckCircle2 } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../common/Toast';
import Button from '../common/Button';
import Input from '../common/Input';
import Card from '../common/Card';
import authService from '../../services/authService';

export default function StorefrontAuth({ onSuccess }) {
  const { login, register } = useAuth();
  const { success } = useToast();

  const [tab, setTab] = useState('login'); // 'login' | 'register' | 'forgot'

  // Login Form State
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [showLoginPassword, setShowLoginPassword] = useState(false);
  const [loginErrors, setLoginErrors] = useState({});
  const [loginApiError, setLoginApiError] = useState('');
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  // Forgot Password State
  const [forgotEmail, setForgotEmail] = useState('');
  const [forgotErrors, setForgotErrors] = useState({});
  const [forgotApiError, setForgotApiError] = useState('');
  const [forgotSuccess, setForgotSuccess] = useState(false);
  const [isSubmittingForgot, setIsSubmittingForgot] = useState(false);

  // Register Form State
  const [regFullName, setRegFullName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPhone, setRegPhone] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [showRegPassword, setShowRegPassword] = useState(false);
  const [regErrors, setRegErrors] = useState({});
  const [regApiError, setRegApiError] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);

  // Quick fill test account
  const handleQuickFillTest = () => {
    setLoginEmail('testuser@example.com');
    setLoginPassword('Test@12345');
    setLoginErrors({});
    setLoginApiError('');
  };

  const validateLogin = () => {
    const errs = {};
    if (!loginEmail.trim()) {
      errs.email = 'Email or username is required';
    }
    if (!loginPassword) {
      errs.password = 'Password is required';
    }
    setLoginErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    setLoginApiError('');

    if (!validateLogin()) return;

    setIsLoggingIn(true);
    try {
      const result = await login(loginEmail.trim().toLowerCase(), loginPassword);
      const userName = result?.user?.first_name || result?.user?.full_name || result?.user?.email || 'Customer';
      success(`Welcome back to Bharat Masala, ${userName}!`, 'Access Granted');
      if (onSuccess) onSuccess(result);
    } catch (err) {
      // Differentiate network failure vs invalid credentials
      if (err.isNetworkError || err.status === 0) {
        setLoginApiError('Unable to connect to the Bharat Masala backend. Please verify your internet connection or that the server is online.');
      } else {
        setLoginApiError(err.userMessage || err.message || 'Invalid email or password. Please check your credentials.');
      }
    } finally {
      setIsLoggingIn(false);
    }
  };

  const validateForgot = () => {
    const errs = {};
    if (!forgotEmail.trim()) {
      errs.email = 'Registered email address is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(forgotEmail.trim())) {
      errs.email = 'Please enter a valid email address';
    }
    setForgotErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleForgotSubmit = async (e) => {
    e.preventDefault();
    setForgotApiError('');

    if (!validateForgot()) return;

    setIsSubmittingForgot(true);
    try {
      await authService.requestPasswordReset(forgotEmail.trim().toLowerCase());
      setForgotSuccess(true);
    } catch (err) {
      if (err.isNetworkError || err.status === 0) {
        setForgotApiError('Unable to connect to the backend server. Please verify your connection.');
      } else {
        setForgotApiError(err.userMessage || err.message || 'Failed to process password reset. Please try again.');
      }
    } finally {
      setIsSubmittingForgot(false);
    }
  };

  const validateRegister = () => {
    const errs = {};
    if (!regFullName.trim()) errs.full_name = 'Full name is required';
    if (!regEmail.trim()) {
      errs.email = 'Email address is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(regEmail.trim())) {
      errs.email = 'Enter a valid email address';
    }
    if (!regPhone.trim()) {
      errs.phone_number = 'Phone number is required';
    } else if (!/^\+?[0-9]{10,13}$/.test(regPhone.replace(/[\s-]/g, ''))) {
      errs.phone_number = 'Enter a valid 10-digit mobile number';
    }
    if (!regPassword) {
      errs.password = 'Password is required';
    } else if (regPassword.length < 8) {
      errs.password = 'Password must be at least 8 characters';
    }
    setRegErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleRegisterSubmit = async (e) => {
    e.preventDefault();
    setRegApiError('');

    if (!validateRegister()) return;

    setIsRegistering(true);
    try {
      const payload = {
        email: regEmail.trim().toLowerCase(),
        password: regPassword,
        confirm_password: regPassword,
        phone_number: regPhone.trim().startsWith('+91') ? regPhone.trim() : `+91${regPhone.replace(/\D/g, '').slice(-10)}`,
        first_name: regFullName.trim().split(' ')[0] || regFullName.trim(),
        last_name: regFullName.trim().split(' ').slice(1).join(' ') || '',
      };
      const result = await register(payload);
      success('Account created successfully! Welcome to Bharat Masala.', 'Account Ready');
      if (onSuccess) onSuccess(result);
    } catch (err) {
      if (err.details && typeof err.details === 'object') {
        const fieldErrors = {};
        for (const [field, msgs] of Object.entries(err.details)) {
          const msg = Array.isArray(msgs) ? msgs.join(' ') : String(msgs);
          if (field === 'email') fieldErrors.email = msg;
          else if (field === 'phone_number') fieldErrors.phone_number = msg;
          else if (field === 'password') fieldErrors.password = msg;
          else if (field === 'first_name' || field === 'full_name') fieldErrors.full_name = msg;
        }
        if (Object.keys(fieldErrors).length > 0) {
          setRegErrors((prev) => ({ ...prev, ...fieldErrors }));
        }
      }

      if (err.isNetworkError || err.status === 0) {
        setRegApiError('Unable to connect to the backend server. Please verify your connection.');
      } else {
        setRegApiError(err.userMessage || err.message || 'Registration failed. Please check your information.');
      }
    } finally {
      setIsRegistering(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#FAF8F5] flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8 relative overflow-hidden">
      {/* Subtle Background Ambience */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-96 bg-gradient-to-b from-saffron-500/10 via-amber-200/5 to-transparent pointer-events-none rounded-b-[4rem]" />

      <div className="w-full max-w-md mx-auto space-y-6 relative z-10">
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
            {tab === 'login'
              ? 'Sign In to Enter the Store'
              : tab === 'register'
              ? 'Create Your Spice Account'
              : 'Recover Your Account'}
          </h1>
          <p className="text-xs text-spice-stone max-w-sm mx-auto">
            {tab === 'login'
              ? 'Access estate-harvested single origin spices, freshly milled masalas, and order tracking'
              : tab === 'register'
              ? 'Join the Bharat Masala family for wholesale rates, express delivery, and farm purity'
              : 'Enter your registered email to receive secure, one-time password reset instructions.'}
          </p>
        </div>

        {/* Tab Selector */}
        {tab !== 'forgot' ? (
          <div className="flex rounded-xl bg-spice-canvas border border-spice-border p-1">
            <button
              type="button"
              onClick={() => setTab('login')}
              className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all ${
                tab === 'login'
                  ? 'bg-white text-spice-black shadow-xs'
                  : 'text-spice-stone hover:text-spice-black'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => setTab('register')}
              className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all ${
                tab === 'register'
                  ? 'bg-white text-spice-black shadow-xs'
                  : 'text-spice-stone hover:text-spice-black'
              }`}
            >
              Create Account
            </button>
          </div>
        ) : (
          <div className="flex justify-start">
            <button
              type="button"
              onClick={() => {
                setTab('login');
                setForgotSuccess(false);
                setForgotApiError('');
              }}
              className="text-xs font-semibold text-saffron-700 hover:text-saffron-800 flex items-center gap-1.5 transition-colors"
            >
              &larr; Back to Sign In
            </button>
          </div>
        )}

        {/* Main Card */}
        <Card variant="elevated" padding="lg" className="rounded-3xl border border-spice-border shadow-card">
          {tab === 'login' ? (
            /* ================= SIGN IN TAB ================= */
            <form noValidate onSubmit={handleLoginSubmit} className="space-y-4">
              {loginApiError && (
                <div
                  role="alert"
                  className="flex items-start gap-2.5 rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-700 animate-slideUp"
                >
                  <AlertCircle className="h-4 w-4 shrink-0 text-red-600 mt-0.5" />
                  <div className="flex-1 font-medium leading-relaxed">{loginApiError}</div>
                </div>
              )}

              {/* Quick Fill Helper for Evaluation */}
              <div className="flex items-center justify-between bg-saffron-50/70 border border-saffron-200/80 rounded-xl px-3 py-2 text-xs">
                <span className="text-[11px] text-saffron-900 font-medium flex items-center gap-1.5">
                  <Sparkles className="h-3.5 w-3.5 text-saffron-600" />
                  <span>Test Account:</span>
                </span>
                <button
                  type="button"
                  onClick={handleQuickFillTest}
                  className="text-[11px] font-bold text-saffron-800 bg-white border border-saffron-300 hover:bg-saffron-100 px-2 py-0.5 rounded-md transition-colors shadow-2xs"
                >
                  Use testuser@example.com
                </button>
              </div>

              <Input
                label="Email Address or Username"
                type="text"
                name="username"
                autoComplete="username"
                required
                value={loginEmail}
                onChange={(e) => {
                  setLoginEmail(e.target.value);
                  if (loginErrors.email) setLoginErrors((prev) => ({ ...prev, email: '' }));
                }}
                error={loginErrors.email}
                leftIcon={<Mail className="h-4 w-4" />}
                placeholder="testuser@example.com"
              />

              <div>
                <Input
                  label="Password"
                  type={showLoginPassword ? 'text' : 'password'}
                  name="password"
                  autoComplete="current-password"
                  required
                  value={loginPassword}
                  onChange={(e) => {
                    setLoginPassword(e.target.value);
                    if (loginErrors.password) setLoginErrors((prev) => ({ ...prev, password: '' }));
                  }}
                  error={loginErrors.password}
                  leftIcon={<Lock className="h-4 w-4" />}
                  rightIcon={
                    <button
                      type="button"
                      onClick={() => setShowLoginPassword(!showLoginPassword)}
                      className="text-spice-stone hover:text-spice-black focus:outline-none"
                      aria-label={showLoginPassword ? 'Hide password' : 'Show password'}
                    >
                      {showLoginPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  }
                  placeholder="••••••••"
                />
                <div className="flex items-center justify-end mt-1.5">
                  <button
                    type="button"
                    onClick={() => {
                      setTab('forgot');
                      setForgotEmail(loginEmail);
                      setForgotApiError('');
                      setForgotSuccess(false);
                    }}
                    className="text-xs font-semibold text-saffron-700 hover:text-saffron-800 hover:underline focus:outline-none"
                  >
                    Forgot Password?
                  </button>
                </div>
              </div>

              <div className="pt-2">
                <Button
                  type="submit"
                  variant="primary"
                  size="lg"
                  isFullWidth
                  isLoading={isLoggingIn}
                  rightIcon={<ArrowRight className="h-4 w-4" />}
                  className="font-semibold uppercase tracking-wider text-xs shadow-saffron-glow"
                >
                  Sign In to Store
                </Button>
              </div>
            </form>
          ) : tab === 'register' ? (
            /* ================= REGISTER TAB ================= */
            <form noValidate onSubmit={handleRegisterSubmit} className="space-y-4">
              {regApiError && (
                <div
                  role="alert"
                  className="flex items-start gap-2.5 rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-700 animate-slideUp"
                >
                  <AlertCircle className="h-4 w-4 shrink-0 text-red-600 mt-0.5" />
                  <div className="flex-1 font-medium leading-relaxed">{regApiError}</div>
                </div>
              )}

              <Input
                label="Full Name"
                type="text"
                name="full_name"
                required
                value={regFullName}
                onChange={(e) => {
                  setRegFullName(e.target.value);
                  if (regErrors.full_name) setRegErrors((prev) => ({ ...prev, full_name: '' }));
                }}
                error={regErrors.full_name}
                leftIcon={<User className="h-4 w-4" />}
                placeholder="e.g. Ramesh Hegde"
              />

              <Input
                label="Email Address"
                type="email"
                name="email"
                required
                value={regEmail}
                onChange={(e) => {
                  setRegEmail(e.target.value);
                  if (regErrors.email) setRegErrors((prev) => ({ ...prev, email: '' }));
                }}
                error={regErrors.email}
                leftIcon={<Mail className="h-4 w-4" />}
                placeholder="ramesh@example.com"
              />

              <Input
                label="Mobile Phone Number"
                type="tel"
                name="phone_number"
                required
                value={regPhone}
                onChange={(e) => {
                  setRegPhone(e.target.value);
                  if (regErrors.phone_number) setRegErrors((prev) => ({ ...prev, phone_number: '' }));
                }}
                error={regErrors.phone_number}
                leftIcon={<Phone className="h-4 w-4" />}
                placeholder="+91 98765 43210"
              />

              <Input
                label="Password"
                type={showRegPassword ? 'text' : 'password'}
                name="password"
                required
                value={regPassword}
                onChange={(e) => {
                  setRegPassword(e.target.value);
                  if (regErrors.password) setRegErrors((prev) => ({ ...prev, password: '' }));
                }}
                error={regErrors.password}
                leftIcon={<Lock className="h-4 w-4" />}
                rightIcon={
                  <button
                    type="button"
                    onClick={() => setShowRegPassword(!showRegPassword)}
                    className="text-spice-stone hover:text-spice-black focus:outline-none"
                    aria-label={showRegPassword ? 'Hide password' : 'Show password'}
                  >
                    {showRegPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                }
                placeholder="Min 8 characters"
              />

              <div className="pt-2">
                <Button
                  type="submit"
                  variant="primary"
                  size="lg"
                  isFullWidth
                  isLoading={isRegistering}
                  rightIcon={<ArrowRight className="h-4 w-4" />}
                  className="font-semibold uppercase tracking-wider text-xs shadow-saffron-glow"
                >
                  Create Account &amp; Enter
                </Button>
              </div>
            </form>
          ) : (
            /* ================= FORGOT PASSWORD TAB ================= */
            forgotSuccess ? (
              <div className="py-4 text-center space-y-4 animate-slideUp">
                <div className="w-14 h-14 bg-cardamom-50 border border-cardamom-200 rounded-full flex items-center justify-center mx-auto text-cardamom-700">
                  <CheckCircle2 className="h-7 w-7" />
                </div>
                <div className="space-y-1">
                  <h2 className="text-base font-bold text-spice-black">Check Your Email</h2>
                  <p className="text-xs text-spice-stone max-w-xs mx-auto leading-relaxed">
                    If an account exists with <span className="font-semibold text-spice-black">{forgotEmail}</span>, you will receive password reset instructions shortly.
                  </p>
                </div>
                <div className="bg-amber-50/70 border border-amber-200/80 rounded-xl p-3 text-[11px] text-amber-800 text-left">
                  <p className="font-semibold mb-0.5">Note on security:</p>
                  <p>Reset links expire after <strong>1 hour</strong>. For privacy and security, we do not confirm whether an address is registered.</p>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="md"
                  isFullWidth
                  onClick={() => {
                    setTab('login');
                    setForgotSuccess(false);
                  }}
                  className="text-xs font-semibold"
                >
                  Return to Sign In
                </Button>
              </div>
            ) : (
              <form noValidate onSubmit={handleForgotSubmit} className="space-y-4">
                {forgotApiError && (
                  <div
                    role="alert"
                    className="flex items-start gap-2.5 rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-700 animate-slideUp"
                  >
                    <AlertCircle className="h-4 w-4 shrink-0 text-red-600 mt-0.5" />
                    <div className="flex-1 font-medium leading-relaxed">{forgotApiError}</div>
                  </div>
                )}

                <p className="text-xs text-spice-stone leading-relaxed">
                  Enter your registered email address below. We will send you a one-time link to securely choose a new password.
                </p>

                <Input
                  label="Registered Email Address"
                  type="email"
                  name="email"
                  autoComplete="email"
                  required
                  value={forgotEmail}
                  onChange={(e) => {
                    setForgotEmail(e.target.value);
                    if (forgotErrors.email) setForgotErrors((prev) => ({ ...prev, email: '' }));
                  }}
                  error={forgotErrors.email}
                  leftIcon={<Mail className="h-4 w-4" />}
                  placeholder="e.g. yourname@example.com"
                />

                <div className="pt-2 space-y-2">
                  <Button
                    type="submit"
                    variant="primary"
                    size="lg"
                    isFullWidth
                    isLoading={isSubmittingForgot}
                    rightIcon={<ArrowRight className="h-4 w-4" />}
                    className="font-semibold uppercase tracking-wider text-xs shadow-saffron-glow"
                  >
                    Send Reset Link
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    isFullWidth
                    onClick={() => {
                      setTab('login');
                      setForgotApiError('');
                    }}
                    className="text-xs text-spice-stone hover:text-spice-black"
                  >
                    Cancel and Return to Sign In
                  </Button>
                </div>
              </form>
            )
          )}

          {/* Footer Assistance & Links */}
          <div className="mt-6 pt-5 border-t border-spice-borderSubtle text-center text-xs space-y-3">
            <div className="flex items-center justify-between text-[11px] text-spice-stone">
              <span className="flex items-center gap-1">
                <ShieldCheck className="h-3.5 w-3.5 text-cardamom-700" />
                <span>256-Bit SSL Encryption</span>
              </span>
              <Link
                href="/admin-login"
                className="font-semibold text-spice-stone hover:text-saffron-700 hover:underline"
              >
                Staff / Admin Portal &rarr;
              </Link>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
