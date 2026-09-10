'use client';

import React, { useState, Suspense } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  User,
  Mail,
  Phone,
  Lock,
  Eye,
  EyeOff,
  Building2,
  FileText,
  ShieldCheck,
  AlertCircle,
  ArrowRight,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../components/common/Toast';
import Button from '../../components/common/Button';
import Input from '../../components/common/Input';
import Select from '../../components/common/Select';
import Card from '../../components/common/Card';

const BUSINESS_TYPES = [
  { value: 'RETAILER', label: 'Retail Spice / Grocery Store' },
  { value: 'DISTRIBUTOR', label: 'Wholesale Distributor' },
  { value: 'RESTAURANT_HOTEL', label: 'Restaurant / Hotel / Cloud Kitchen' },
  { value: 'PROPRIETORSHIP', label: 'Sole Proprietorship' },
  { value: 'PARTNERSHIP', label: 'Partnership Firm' },
  { value: 'LLP', label: 'Limited Liability Partnership (LLP)' },
  { value: 'PRIVATE_LIMITED', label: 'Private Limited Company' },
  { value: 'PUBLIC_LIMITED', label: 'Public Limited Company' },
  { value: 'OTHER', label: 'Other Commercial Enterprise' },
];

function RegisterForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialTab = searchParams.get('tab') === 'wholesale' ? 'wholesale' : 'retail';

  const [activeTab, setActiveTab] = useState(initialTab);
  const { register, registerWholesale } = useAuth();
  const { success } = useToast();

  // Retail Form State
  const [retailData, setRetailData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone_number: '',
    password: '',
    confirm_password: '',
  });

  // Wholesale Form State
  const [wholesaleData, setWholesaleData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone_number: '',
    password: '',
    confirm_password: '',
    company_name: '',
    gstin: '',
    pan_number: '',
    fssai_license: '',
    business_type: 'RETAILER',
  });

  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState({});
  const [apiError, setApiError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const validateRetail = () => {
    const errs = {};
    if (!retailData.email.trim()) {
      errs.email = 'Email address is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(retailData.email.trim())) {
      errs.email = 'Enter a valid email address';
    }

    if (!retailData.phone_number.trim()) {
      errs.phone_number = 'Mobile number is required';
    } else if (!/^(\+91|91)?[6-9]\d{9}$/.test(retailData.phone_number.replace(/\s+/g, ''))) {
      errs.phone_number = 'Enter a valid 10-digit Indian mobile number';
    }

    if (!retailData.password) {
      errs.password = 'Password is required';
    } else if (retailData.password.length < 8) {
      errs.password = 'Password must be at least 8 characters';
    }

    if (retailData.password !== retailData.confirm_password) {
      errs.confirm_password = 'Passwords do not match';
    }

    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const validateWholesale = () => {
    const errs = {};
    if (!wholesaleData.email.trim()) {
      errs.email = 'Email address is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(wholesaleData.email.trim())) {
      errs.email = 'Enter a valid email address';
    }

    if (!wholesaleData.phone_number.trim()) {
      errs.phone_number = 'Mobile number is required';
    } else if (!/^(\+91|91)?[6-9]\d{9}$/.test(wholesaleData.phone_number.replace(/\s+/g, ''))) {
      errs.phone_number = 'Enter a valid 10-digit Indian mobile number';
    }

    if (!wholesaleData.password) {
      errs.password = 'Password is required';
    } else if (wholesaleData.password.length < 8) {
      errs.password = 'Password must be at least 8 characters';
    }

    if (wholesaleData.password !== wholesaleData.confirm_password) {
      errs.confirm_password = 'Passwords do not match';
    }

    if (!wholesaleData.company_name.trim()) {
      errs.company_name = 'Registered business or company name is required';
    }

    const cleanGstin = wholesaleData.gstin.trim().toUpperCase();
    if (!cleanGstin) {
      errs.gstin = 'GSTIN is required for wholesale tax invoice verification';
    } else if (!/^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}$/.test(cleanGstin)) {
      errs.gstin = 'Invalid GSTIN format (e.g. 29ABCDE1234F1Z5)';
    }

    const cleanPan = wholesaleData.pan_number.trim().toUpperCase();
    if (!cleanPan) {
      errs.pan_number = 'PAN number is required';
    } else if (!/^[A-Z]{5}\d{4}[A-Z]{1}$/.test(cleanPan)) {
      errs.pan_number = 'Invalid PAN format (e.g. ABCDE1234F)';
    }

    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setApiError('');

    if (activeTab === 'retail') {
      if (!validateRetail()) return;

      setIsSubmitting(true);
      try {
        await register({
          email: retailData.email.trim().toLowerCase(),
          phone_number: retailData.phone_number.trim(),
          password: retailData.password,
          confirm_password: retailData.confirm_password,
          first_name: retailData.first_name.trim(),
          last_name: retailData.last_name.trim(),
        });
        success('Account created successfully! Welcome to Bharat Masala.', 'Welcome');
        router.replace('/account');
      } catch (err) {
        if (err.details && typeof err.details === 'object') {
          const fieldErrors = {};
          for (const [field, msgs] of Object.entries(err.details)) {
            fieldErrors[field] = Array.isArray(msgs) ? msgs.join(' ') : String(msgs);
          }
          setErrors((prev) => ({ ...prev, ...fieldErrors }));
        }
        setApiError(err.userMessage || err.message || 'Registration failed. Please verify your details.');
      } finally {
        setIsSubmitting(false);
      }
    } else {
      if (!validateWholesale()) return;

      setIsSubmitting(true);
      try {
        await registerWholesale({
          user: {
            email: wholesaleData.email.trim().toLowerCase(),
            phone_number: wholesaleData.phone_number.trim(),
            password: wholesaleData.password,
            confirm_password: wholesaleData.confirm_password,
            first_name: wholesaleData.first_name.trim(),
            last_name: wholesaleData.last_name.trim(),
          },
          company_name: wholesaleData.company_name.trim(),
          gstin: wholesaleData.gstin.trim().toUpperCase(),
          pan_number: wholesaleData.pan_number.trim().toUpperCase(),
          fssai_license: wholesaleData.fssai_license.trim(),
          business_type: wholesaleData.business_type,
        });
        success('Wholesale application submitted! Verification pending with manager.', 'Submitted');
        router.replace('/account');
      } catch (err) {
        setApiError(err.message || 'Wholesale registration failed. Please verify your tax documents.');
      } finally {
        setIsSubmitting(false);
      }
    }
  };

  return (
    <div className="min-h-[85vh] flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="w-full max-w-xl space-y-6">
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
            Create Your Account
          </h1>
          <p className="text-xs text-spice-stone mt-1">
            Join the Western Ghats single-origin spice community
          </p>
        </div>

        {/* Tab Selector */}
        <div className="flex rounded-xl bg-spice-canvas p-1 border border-spice-border">
          <button
            type="button"
            onClick={() => {
              setActiveTab('retail');
              setErrors({});
              setApiError('');
            }}
            className={`flex-1 py-2.5 text-xs font-semibold rounded-lg transition-all ${
              activeTab === 'retail'
                ? 'bg-white text-spice-black shadow-xs'
                : 'text-spice-stone hover:text-spice-black'
            }`}
          >
            Retail Customer
          </button>
          <button
            type="button"
            onClick={() => {
              setActiveTab('wholesale');
              setErrors({});
              setApiError('');
            }}
            className={`flex-1 py-2.5 text-xs font-semibold rounded-lg transition-all flex items-center justify-center gap-1.5 ${
              activeTab === 'wholesale'
                ? 'bg-cardamom-700 text-white shadow-xs'
                : 'text-spice-stone hover:text-spice-black'
            }`}
          >
            <Building2 className="h-3.5 w-3.5" />
            <span>Wholesale B2B Buyer</span>
          </button>
        </div>

        {/* Form Container */}
        <Card variant="elevated" padding="lg" className="rounded-2xl">
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
            {activeTab === 'retail' ? (
              /* Retail Fields */
              <>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <Input
                    label="First Name"
                    value={retailData.first_name}
                    onChange={(e) => setRetailData({ ...retailData, first_name: e.target.value })}
                    leftIcon={<User className="h-4 w-4" />}
                    placeholder="Aarav"
                  />
                  <Input
                    label="Last Name"
                    value={retailData.last_name}
                    onChange={(e) => setRetailData({ ...retailData, last_name: e.target.value })}
                    placeholder="Sharma"
                  />
                </div>

                <Input
                  label="Email Address"
                  type="email"
                  required
                  value={retailData.email}
                  onChange={(e) => {
                    setRetailData({ ...retailData, email: e.target.value });
                    if (errors.email) setErrors((prev) => ({ ...prev, email: '' }));
                  }}
                  error={errors.email}
                  leftIcon={<Mail className="h-4 w-4" />}
                  placeholder="name@example.com"
                />

                <Input
                  label="Mobile Number (India)"
                  type="tel"
                  required
                  value={retailData.phone_number}
                  onChange={(e) => {
                    setRetailData({ ...retailData, phone_number: e.target.value });
                    if (errors.phone_number) setErrors((prev) => ({ ...prev, phone_number: '' }));
                  }}
                  error={errors.phone_number}
                  helperText="Required for order delivery SMS updates"
                  leftIcon={<Phone className="h-4 w-4" />}
                  placeholder="9876543210"
                />

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <Input
                    label="Password"
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={retailData.password}
                    onChange={(e) => {
                      setRetailData({ ...retailData, password: e.target.value });
                      if (errors.password) setErrors((prev) => ({ ...prev, password: '' }));
                    }}
                    error={errors.password}
                    leftIcon={<Lock className="h-4 w-4" />}
                    placeholder="Min 8 characters"
                  />
                  <Input
                    label="Confirm Password"
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={retailData.confirm_password}
                    onChange={(e) => {
                      setRetailData({ ...retailData, confirm_password: e.target.value });
                      if (errors.confirm_password)
                        setErrors((prev) => ({ ...prev, confirm_password: '' }));
                    }}
                    error={errors.confirm_password}
                    leftIcon={<Lock className="h-4 w-4" />}
                    rightIcon={
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="text-spice-stone hover:text-spice-black"
                      >
                        {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    }
                    placeholder="Re-enter password"
                  />
                </div>
              </>
            ) : (
              /* Wholesale B2B Fields */
              <>
                <div className="rounded-xl bg-cardamom-50 border border-cardamom-200 p-3 mb-2 text-xs text-cardamom-900">
                  <div className="flex items-center gap-1.5 font-bold mb-0.5">
                    <ShieldCheck className="h-4 w-4 text-cardamom-700" />
                    <span>Wholesale Buyer Requirements</span>
                  </div>
                  <p className="text-[11px] text-cardamom-800">
                    B2B buyers gain access to bulk quantity slabs, commercial trade rates, and verified GST tax invoices.
                  </p>
                </div>

                <Input
                  label="Registered Company / Business Name"
                  required
                  value={wholesaleData.company_name}
                  onChange={(e) => {
                    setWholesaleData({ ...wholesaleData, company_name: e.target.value });
                    if (errors.company_name) setErrors((prev) => ({ ...prev, company_name: '' }));
                  }}
                  error={errors.company_name}
                  leftIcon={<Building2 className="h-4 w-4" />}
                  placeholder="e.g. Malenadu Grocers Pvt Ltd"
                />

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <Input
                    label="GSTIN (15 Chars)"
                    required
                    value={wholesaleData.gstin}
                    onChange={(e) => {
                      setWholesaleData({ ...wholesaleData, gstin: e.target.value.toUpperCase() });
                      if (errors.gstin) setErrors((prev) => ({ ...prev, gstin: '' }));
                    }}
                    error={errors.gstin}
                    leftIcon={<FileText className="h-4 w-4" />}
                    placeholder="29ABCDE1234F1Z5"
                  />

                  <Input
                    label="PAN Number (10 Chars)"
                    required
                    value={wholesaleData.pan_number}
                    onChange={(e) => {
                      setWholesaleData({ ...wholesaleData, pan_number: e.target.value.toUpperCase() });
                      if (errors.pan_number) setErrors((prev) => ({ ...prev, pan_number: '' }));
                    }}
                    error={errors.pan_number}
                    placeholder="ABCDE1234F"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <Input
                    label="FSSAI License (Optional)"
                    value={wholesaleData.fssai_license}
                    onChange={(e) =>
                      setWholesaleData({ ...wholesaleData, fssai_license: e.target.value })
                    }
                    placeholder="14-digit license"
                  />

                  <Select
                    label="Business Entity Type"
                    value={wholesaleData.business_type}
                    onChange={(e) =>
                      setWholesaleData({ ...wholesaleData, business_type: e.target.value })
                    }
                    options={BUSINESS_TYPES}
                  />
                </div>

                <div className="border-t border-spice-borderSubtle pt-3">
                  <p className="text-xs font-bold uppercase tracking-wider text-spice-stone mb-2">
                    Authorized Contact Person
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
                    <Input
                      label="Contact First Name"
                      value={wholesaleData.first_name}
                      onChange={(e) =>
                        setWholesaleData({ ...wholesaleData, first_name: e.target.value })
                      }
                      placeholder="Ramesh"
                    />
                    <Input
                      label="Contact Last Name"
                      value={wholesaleData.last_name}
                      onChange={(e) =>
                        setWholesaleData({ ...wholesaleData, last_name: e.target.value })
                      }
                      placeholder="Kannan"
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
                    <Input
                      label="Official Business Email"
                      type="email"
                      required
                      value={wholesaleData.email}
                      onChange={(e) => {
                        setWholesaleData({ ...wholesaleData, email: e.target.value });
                        if (errors.email) setErrors((prev) => ({ ...prev, email: '' }));
                      }}
                      error={errors.email}
                      leftIcon={<Mail className="h-4 w-4" />}
                      placeholder="merchant@company.com"
                    />

                    <Input
                      label="Mobile Number"
                      type="tel"
                      required
                      value={wholesaleData.phone_number}
                      onChange={(e) => {
                        setWholesaleData({ ...wholesaleData, phone_number: e.target.value });
                        if (errors.phone_number)
                          setErrors((prev) => ({ ...prev, phone_number: '' }));
                      }}
                      error={errors.phone_number}
                      leftIcon={<Phone className="h-4 w-4" />}
                      placeholder="9876543211"
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <Input
                      label="Password"
                      type={showPassword ? 'text' : 'password'}
                      required
                      value={wholesaleData.password}
                      onChange={(e) => {
                        setWholesaleData({ ...wholesaleData, password: e.target.value });
                        if (errors.password) setErrors((prev) => ({ ...prev, password: '' }));
                      }}
                      error={errors.password}
                      leftIcon={<Lock className="h-4 w-4" />}
                      placeholder="Min 8 characters"
                    />
                    <Input
                      label="Confirm Password"
                      type={showPassword ? 'text' : 'password'}
                      required
                      value={wholesaleData.confirm_password}
                      onChange={(e) => {
                        setWholesaleData({
                          ...wholesaleData,
                          confirm_password: e.target.value,
                        });
                        if (errors.confirm_password)
                          setErrors((prev) => ({ ...prev, confirm_password: '' }));
                      }}
                      error={errors.confirm_password}
                      leftIcon={<Lock className="h-4 w-4" />}
                      placeholder="Re-enter password"
                    />
                  </div>
                </div>
              </>
            )}

            <div className="pt-3">
              <Button
                type="submit"
                variant={activeTab === 'wholesale' ? 'secondary' : 'primary'}
                size="lg"
                isFullWidth
                isLoading={isSubmitting}
                rightIcon={<ArrowRight className="h-4 w-4" />}
                className="font-semibold uppercase tracking-wider text-xs"
              >
                {activeTab === 'wholesale'
                  ? 'Submit Wholesale Application'
                  : 'Create Retail Account'}
              </Button>
            </div>
          </form>

          {/* Login Link */}
          <div className="mt-6 pt-4 border-t border-spice-borderSubtle text-center text-xs">
            <p className="text-spice-stone">
              Already registered?{' '}
              <Link
                href="/login"
                className="font-semibold text-saffron-700 hover:text-saffron-800 hover:underline"
              >
                Sign In to your account
              </Link>
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
}

export default function RegisterPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-[80vh] flex items-center justify-center">
          <div className="h-8 w-8 rounded-full border-2 border-saffron-600 border-t-transparent animate-spin" />
        </div>
      }
    >
      <RegisterForm />
    </Suspense>
  );
}
