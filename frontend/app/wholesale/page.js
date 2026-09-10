'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import {
  Building2,
  ShieldCheck,
  Package,
  FileCheck,
  TrendingDown,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  Lock,
  Sparkles,
} from 'lucide-react';
import Button from '../../components/common/Button';
import Input from '../../components/common/Input';
import Select from '../../components/common/Select';
import Badge from '../../components/common/Badge';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../components/common/Toast';
import authService from '../../services/authService';

const BUSINESS_TYPE_OPTIONS = [
  { value: 'HORECA', label: 'Hotel / Restaurant / Cafe (HoReCa)' },
  { value: 'RETAILER', label: 'Retail Store / Supermarket' },
  { value: 'DISTRIBUTOR', label: 'Distributor / Wholesaler' },
  { value: 'OTHER', label: 'Other Enterprise' },
];

export default function WholesalePage() {
  const { user, isAuthenticated, isWholesale } = useAuth();
  const { success, error: showToastError } = useToast();

  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    phone: '',
    password: '',
    confirmPassword: '',
    companyName: '',
    gstin: '',
    panNumber: '',
    fssaiLicense: '',
    businessType: 'HORECA',
  });

  const [isLoading, setIsLoading] = useState(false);
  const [formError, setFormError] = useState('');
  const [submittedSuccessfully, setSubmittedSuccessfully] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError('');

    // Validation
    if (!formData.companyName.trim()) {
      setFormError('Company or Business name is required.');
      return;
    }

    const gstinRegex = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;
    const cleanGstin = formData.gstin.trim().toUpperCase();
    if (!gstinRegex.test(cleanGstin)) {
      setFormError('Please enter a valid 15-character Indian GSTIN (e.g. 29AAAAA0000A1Z5).');
      return;
    }

    const panRegex = /^[A-Z]{5}[0-9]{4}[A-Z]{1}$/;
    const cleanPan = formData.panNumber.trim().toUpperCase();
    if (!panRegex.test(cleanPan)) {
      setFormError('Please enter a valid 10-character Indian PAN number (e.g. AAAAA0000A).');
      return;
    }

    if (formData.password.length < 8) {
      setFormError('Password must be at least 8 characters long.');
      return;
    }

    if (formData.password !== formData.confirmPassword) {
      setFormError('Passwords do not match.');
      return;
    }

    setIsLoading(true);

    const payload = {
      user: {
        first_name: formData.firstName.trim(),
        last_name: formData.lastName.trim(),
        email: formData.email.trim().toLowerCase(),
        phone_number: formData.phone.trim().startsWith('+91')
          ? formData.phone.trim()
          : `+91${formData.phone.trim().replace(/^0+/, '')}`,
        password: formData.password,
        confirm_password: formData.confirmPassword,
      },
      company_name: formData.companyName.trim(),
      gstin: cleanGstin,
      pan_number: cleanPan,
      fssai_license: formData.fssaiLicense.trim(),
      business_type: formData.businessType,
    };

    try {
      const res = await authService.registerWholesale(payload);
      setSubmittedSuccessfully(true);
      success(
        res?._message || 'Wholesale application submitted! Our commercial desk will review your credentials.',
        'Application Submitted'
      );
    } catch (err) {
      console.error('Wholesale registration failure:', err);
      setFormError(err.message || 'Failed to submit wholesale application. Please verify your details.');
      showToastError(err.message || 'Submission failed. Please check form errors.', 'Wholesale Application');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-spice-canvas">
      {/* Hero Strip */}
      <section className="relative py-14 sm:py-20 bg-gradient-to-b from-stone-900 via-spice-earth to-stone-900 text-white">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center space-y-5">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-saffron-600/30 border border-saffron-400/30 text-xs font-semibold text-saffron-300">
            <Building2 className="h-3.5 w-3.5 text-saffron-400" />
            <span>Commercial &amp; Institutional Sourcing</span>
          </div>

          <h1 className="text-3xl sm:text-5xl font-display font-extrabold tracking-tight text-white">
            Estate-Direct B2B Wholesale Spices
          </h1>

          <p className="text-sm sm:text-base text-stone-300 max-w-2xl mx-auto leading-relaxed">
            Supplying India’s premier culinary establishments, gourmet hotels, craft distillers, and export distributors with laboratory-verified, cold-milled single-origin Western Ghats spices.
          </p>
        </div>
      </section>

      {/* Key Benefits Grid */}
      <section className="py-12 bg-white border-b border-spice-borderSubtle">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="p-5 rounded-2xl bg-spice-canvas border border-spice-border space-y-2">
              <TrendingDown className="h-6 w-6 text-saffron-700" />
              <h3 className="text-sm font-bold text-spice-black font-display">Tiered Slab Pricing</h3>
              <p className="text-xs text-spice-stone leading-relaxed">
                Volume discounts starting from 10kg, 25kg, 50kg, and 100kg bulk procurement lots.
              </p>
            </div>

            <div className="p-5 rounded-2xl bg-spice-canvas border border-spice-border space-y-2">
              <FileCheck className="h-6 w-6 text-emerald-700" />
              <h3 className="text-sm font-bold text-spice-black font-display">Batch COA Guarantee</h3>
              <p className="text-xs text-spice-stone leading-relaxed">
                Every consignment includes NABL-accredited laboratory test reports for piperine, curcumin, and volatile oils.
              </p>
            </div>

            <div className="p-5 rounded-2xl bg-spice-canvas border border-spice-border space-y-2">
              <Package className="h-6 w-6 text-amber-700" />
              <h3 className="text-sm font-bold text-spice-black font-display">Nitrogen Bulk Barrier Packs</h3>
              <p className="text-xs text-spice-stone leading-relaxed">
                5kg, 10kg, and 25kg multi-layer vacuum pouches with nitrogen flushing to maintain aroma over long storage.
              </p>
            </div>

            <div className="p-5 rounded-2xl bg-spice-canvas border border-spice-border space-y-2">
              <ShieldCheck className="h-6 w-6 text-stone-700" />
              <h3 className="text-sm font-bold text-spice-black font-display">Dedicated Commercial Desk</h3>
              <p className="text-xs text-spice-stone leading-relaxed">
                Priority logistics dispatch, GST compliance, and customized grinding fineness upon request.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Main Content Area */}
      <section className="py-14 sm:py-20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Status 1: Approved Wholesale Account */}
          {isAuthenticated && isWholesale ? (
            <div className="rounded-3xl p-8 sm:p-10 bg-emerald-50 border border-emerald-200 text-center space-y-4">
              <div className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
                <CheckCircle2 className="h-6 w-6" />
              </div>
              <div>
                <Badge variant="cardamom" size="sm">
                  Wholesale Partner Approved
                </Badge>
                <h2 className="text-xl font-bold font-display text-emerald-950 mt-2">
                  Welcome to the Bharat Masala B2B Portal
                </h2>
                <p className="text-xs sm:text-sm text-emerald-800 max-w-md mx-auto mt-1">
                  Your commercial account is fully active. Tiered wholesale slab pricing is automatically applied across our catalog.
                </p>
              </div>

              <div className="pt-2">
                <Link href="/products">
                  <Button variant="primary" size="md" rightIcon={<ArrowRight className="h-4 w-4" />}>
                    Browse Wholesale Spice Catalog &rarr;
                  </Button>
                </Link>
              </div>
            </div>
          ) : isAuthenticated && user?.role === 'WHOLESALE_PENDING' ? (
            /* Status 2: Pending Verification */
            <div className="rounded-3xl p-8 sm:p-10 bg-amber-50 border border-amber-200 text-center space-y-4">
              <div className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-amber-100 text-amber-700">
                <FileCheck className="h-6 w-6" />
              </div>
              <div>
                <Badge variant="stone" size="sm">
                  KYC Verification Pending
                </Badge>
                <h2 className="text-xl font-bold font-display text-amber-950 mt-2">
                  Your Wholesale Application is Under Review
                </h2>
                <p className="text-xs sm:text-sm text-amber-800 max-w-md mx-auto mt-1">
                  Our commercial compliance team is reviewing your GSTIN and business credentials. You will receive an email confirmation once activated.
                </p>
              </div>
            </div>
          ) : submittedSuccessfully ? (
            /* Status 3: Application Just Submitted */
            <div className="rounded-3xl p-8 sm:p-10 bg-emerald-50 border border-emerald-200 text-center space-y-4">
              <div className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
                <CheckCircle2 className="h-6 w-6" />
              </div>
              <h2 className="text-xl font-bold font-display text-emerald-950">
                Wholesale Application Received
              </h2>
              <p className="text-xs sm:text-sm text-emerald-800 max-w-md mx-auto">
                Thank you for applying for a commercial account. An operations specialist will verify your GSTIN credentials within 1 business day.
              </p>
              <div className="pt-2">
                <Link href="/">
                  <Button variant="outline-stone" size="sm">
                    Return to Homepage
                  </Button>
                </Link>
              </div>
            </div>
          ) : (
            /* Status 4: Registration Form */
            <div className="rounded-3xl p-6 sm:p-10 bg-white border border-spice-border shadow-sm space-y-8">
              <div>
                <h2 className="text-xl sm:text-2xl font-bold font-display text-spice-black">
                  Apply for a B2B Wholesale Account
                </h2>
                <p className="text-xs sm:text-sm text-spice-stone mt-1">
                  Register your business entity to unlock tiered bulk pricing, credit terms, and direct estate supply contracts.
                </p>
              </div>

              {formError && (
                <div className="p-4 rounded-xl bg-red-50 border border-red-200 flex items-start gap-3 text-xs text-red-800">
                  <AlertTriangle className="h-4 w-4 text-red-600 shrink-0 mt-0.5" />
                  <div>
                    <strong className="font-bold block">Application Error</strong>
                    <p className="mt-0.5">{formError}</p>
                  </div>
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-6">
                {/* Section 1: Business Profile */}
                <div className="space-y-4">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-saffron-700 flex items-center gap-1.5">
                    <Building2 className="h-3.5 w-3.5" />
                    <span>1. Business Entity &amp; Tax Information</span>
                  </h3>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="sm:col-span-2">
                      <Input
                        label="Registered Business / Legal Entity Name"
                        name="companyName"
                        value={formData.companyName}
                        onChange={handleChange}
                        placeholder="e.g. Taj Culinary Enterprises LLP"
                        required
                      />
                    </div>

                    <Select
                      label="Business Classification"
                      name="businessType"
                      value={formData.businessType}
                      onChange={handleChange}
                      options={BUSINESS_TYPE_OPTIONS}
                      required
                    />

                    <Input
                      label="Indian GSTIN (15 Characters)"
                      name="gstin"
                      value={formData.gstin}
                      onChange={handleChange}
                      placeholder="e.g. 29AAAAA0000A1Z5"
                      maxLength={15}
                      required
                    />

                    <Input
                      label="Business PAN (10 Characters)"
                      name="panNumber"
                      value={formData.panNumber}
                      onChange={handleChange}
                      placeholder="e.g. AAAAA0000A"
                      maxLength={10}
                      required
                    />

                    <Input
                      label="FSSAI License Number (Optional)"
                      name="fssaiLicense"
                      value={formData.fssaiLicense}
                      onChange={handleChange}
                      placeholder="e.g. 11223344556677"
                      maxLength={14}
                    />
                  </div>
                </div>

                {/* Section 2: Contact Person */}
                <div className="space-y-4 pt-4 border-t border-spice-borderSubtle">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-saffron-700 flex items-center gap-1.5">
                    <Sparkles className="h-3.5 w-3.5" />
                    <span>2. Authorized Contact Representative</span>
                  </h3>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <Input
                      label="First Name"
                      name="firstName"
                      value={formData.firstName}
                      onChange={handleChange}
                      placeholder="e.g. Rajesh"
                      required
                    />

                    <Input
                      label="Last Name"
                      name="lastName"
                      value={formData.lastName}
                      onChange={handleChange}
                      placeholder="e.g. Hegde"
                      required
                    />

                    <Input
                      label="Work Email Address"
                      type="email"
                      name="email"
                      value={formData.email}
                      onChange={handleChange}
                      placeholder="procurement@yourcompany.com"
                      required
                    />

                    <Input
                      label="Mobile Phone Number"
                      type="tel"
                      name="phone"
                      value={formData.phone}
                      onChange={handleChange}
                      placeholder="9876543210"
                      required
                    />
                  </div>
                </div>

                {/* Section 3: Credentials */}
                <div className="space-y-4 pt-4 border-t border-spice-borderSubtle">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-saffron-700 flex items-center gap-1.5">
                    <Lock className="h-3.5 w-3.5" />
                    <span>3. Account Security</span>
                  </h3>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <Input
                      label="Password"
                      type="password"
                      name="password"
                      value={formData.password}
                      onChange={handleChange}
                      placeholder="Minimum 8 characters"
                      required
                    />

                    <Input
                      label="Confirm Password"
                      type="password"
                      name="confirmPassword"
                      value={formData.confirmPassword}
                      onChange={handleChange}
                      placeholder="Repeat password"
                      required
                    />
                  </div>
                </div>

                <div className="pt-4">
                  <Button
                    type="submit"
                    variant="primary"
                    size="lg"
                    isFullWidth
                    isLoading={isLoading}
                    rightIcon={<ArrowRight className="h-4 w-4" />}
                  >
                    Submit Wholesale Application
                  </Button>
                  <p className="text-[11px] text-spice-muted text-center mt-2.5">
                    By submitting, you agree to our Terms of Sale and statutory B2B GST invoicing compliance.
                  </p>
                </div>
              </form>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
