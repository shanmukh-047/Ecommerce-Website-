'use client';

import React from 'react';
import Link from 'next/link';
import { RotateCcw, ShieldCheck, AlertTriangle, CheckCircle2, ArrowRight } from 'lucide-react';
import Button from '../../components/common/Button';

export default function ReturnsPolicyPage() {
  return (
    <div className="min-h-screen bg-spice-canvas py-12 sm:py-16">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 space-y-10">
        <div className="text-center space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-saffron-100 text-xs font-semibold text-saffron-800">
            <RotateCcw className="h-3.5 w-3.5" />
            <span>Buyer Protection &amp; Quality Guarantee</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-display font-extrabold text-spice-black">
            Returns, Replacement &amp; Refunds Policy
          </h1>
          <p className="text-xs sm:text-sm text-spice-stone max-w-lg mx-auto">
            Our commitment to purity and uncompromising hygiene under FSSAI food safety regulations.
          </p>
        </div>

        <div className="rounded-3xl p-6 sm:p-10 bg-white border border-spice-border shadow-xs space-y-8 text-xs sm:text-sm text-spice-stone leading-relaxed">
          {/* Section 1 */}
          <section className="space-y-3">
            <h2 className="text-base sm:text-lg font-bold font-display text-spice-black flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-emerald-600" />
              <span>1. 7-Day Replacement for Damaged or Defective Items</span>
            </h2>
            <p>
              Due to strict food safety guidelines, opened or unsealed edible spice products cannot be returned for resale. However, if your order arrives:
            </p>
            <ul className="list-disc pl-5 space-y-1 text-spice-black">
              <li>With damaged packaging or broken tamper-evident seals in transit</li>
              <li>With incorrect items or missing variants compared to your invoice</li>
              <li>With verified quality deviations or moisture intrusion</li>
            </ul>
            <p className="pt-1">
              We provide a <strong className="text-spice-black font-semibold">100% free immediate replacement or full refund</strong> within 7 days of package delivery.
            </p>
          </section>

          {/* Section 2 */}
          <section className="space-y-3 pt-6 border-t border-spice-borderSubtle">
            <h2 className="text-base sm:text-lg font-bold font-display text-spice-black flex items-center gap-2">
              <RotateCcw className="h-5 w-5 text-saffron-600" />
              <span>2. How to Request an RMA (Return Merchandise Authorization)</span>
            </h2>
            <ol className="list-decimal pl-5 space-y-2 text-spice-black">
              <li>
                Log into your account and navigate to <Link href="/account/orders" className="text-saffron-700 underline font-semibold">My Orders</Link>.
              </li>
              <li>Select the delivered order and click &ldquo;Request Return / Replacement&rdquo;.</li>
              <li>Attach a clear photograph showing the damaged consignment box and product seal batch number.</li>
              <li>Our customer care desk will review your claim and dispatch a replacement consignment within 24 hours.</li>
            </ol>
          </section>

          {/* Section 3 */}
          <section className="space-y-3 pt-6 border-t border-spice-borderSubtle">
            <h2 className="text-base sm:text-lg font-bold font-display text-spice-black flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-saffron-600" />
              <span>3. Refund Processing &amp; Bank Timelines</span>
            </h2>
            <p>
              When a refund is approved by our operations desk, the amount is credited back to your original payment method (UPI, Debit/Credit Card, or Netbanking account via Razorpay) within <strong className="text-spice-black font-semibold">5 to 7 operational banking days</strong>.
            </p>
            <p className="text-xs text-spice-muted">
              A computerized Credit Note with corresponding GST reversal details will be generated and made available in your order invoices section.
            </p>
          </section>

          <div className="pt-4 flex items-center justify-between border-t border-spice-borderSubtle">
            <Link href="/account/orders">
              <Button variant="primary" size="md">
                View My Orders &rarr;
              </Button>
            </Link>
            <Link href="/contact">
              <Button variant="ghost" size="md">
                Contact Customer Support
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
