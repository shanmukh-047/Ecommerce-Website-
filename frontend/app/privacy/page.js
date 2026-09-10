'use client';

import React from 'react';
import { ShieldCheck, Lock, EyeOff, Server } from 'lucide-react';

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-spice-canvas py-12 sm:py-16">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 space-y-10">
        <div className="text-center space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-saffron-100 text-xs font-semibold text-saffron-800">
            <ShieldCheck className="h-3.5 w-3.5" />
            <span>Security &amp; Confidentiality</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-display font-extrabold text-spice-black">
            Privacy Policy &amp; Data Protection
          </h1>
          <p className="text-xs sm:text-sm text-spice-stone max-w-lg mx-auto">
            How Bharat Masala protects your personal information, delivery addresses, and payment privacy.
          </p>
        </div>

        <div className="rounded-3xl p-6 sm:p-10 bg-white border border-spice-border shadow-xs space-y-8 text-xs sm:text-sm text-spice-stone leading-relaxed">
          <section className="space-y-3">
            <h2 className="text-base sm:text-lg font-bold font-display text-spice-black flex items-center gap-2">
              <Lock className="h-5 w-5 text-saffron-600" />
              <span>1. Information We Collect</span>
            </h2>
            <p>
              When you register an account, place an order, or apply for wholesale credentials, we collect only the necessary information required for fulfillment and statutory tax compliance:
            </p>
            <ul className="list-disc pl-5 space-y-1 text-spice-black">
              <li>Customer contact details: Name, Email Address, and Verified Indian Mobile Number.</li>
              <li>Consignment delivery addresses: Street address, Landmark, City, State, and 6-digit PIN code.</li>
              <li>For B2B wholesale buyers: Company Legal Name, GSTIN, PAN, and Business Classification.</li>
            </ul>
          </section>

          <section className="space-y-3 pt-6 border-t border-spice-borderSubtle">
            <h2 className="text-base sm:text-lg font-bold font-display text-spice-black flex items-center gap-2">
              <EyeOff className="h-5 w-5 text-emerald-600" />
              <span>2. Zero Storage of Payment Credentials</span>
            </h2>
            <p>
              Bharat Masala does <strong className="text-spice-black font-semibold">NOT collect, process, or store</strong> credit/debit card numbers, CVV codes, netbanking passwords, or UPI PINs.
            </p>
            <p>
              All online transactions are processed through RBI-authorized, PCI-DSS Level 1 compliant gateway infrastructure provided by <strong className="text-spice-black font-semibold">Razorpay</strong>. Communication between your browser, our servers, and the banking networks is protected with 256-bit TLS encryption.
            </p>
          </section>

          <section className="space-y-3 pt-6 border-t border-spice-borderSubtle">
            <h2 className="text-base sm:text-lg font-bold font-display text-spice-black flex items-center gap-2">
              <Server className="h-5 w-5 text-saffron-600" />
              <span>3. How We Use &amp; Protect Your Data</span>
            </h2>
            <p>
              Your data is strictly used to fulfill spice consignments, generate legal GST invoices, provide automated SMS/WhatsApp delivery updates, and notify you of new seasonal harvests if subscribed.
            </p>
            <p>
              We <strong className="text-spice-black font-semibold">never sell, rent, or trade</strong> your personal information to third-party marketing brokers or advertising networks.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
