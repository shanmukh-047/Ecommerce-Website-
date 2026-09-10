'use client';

import React from 'react';
import { Scale, FileText, CheckCircle2 } from 'lucide-react';

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-spice-canvas py-12 sm:py-16">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 space-y-10">
        <div className="text-center space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-saffron-100 text-xs font-semibold text-saffron-800">
            <Scale className="h-3.5 w-3.5" />
            <span>Legal Agreement</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-display font-extrabold text-spice-black">
            Terms of Service &amp; Conditions of Sale
          </h1>
          <p className="text-xs sm:text-sm text-spice-stone max-w-lg mx-auto">
            Governing your access and commercial transactions on Bharat Masala e-commerce platform.
          </p>
        </div>

        <div className="rounded-3xl p-6 sm:p-10 bg-white border border-spice-border shadow-xs space-y-8 text-xs sm:text-sm text-spice-stone leading-relaxed">
          <section className="space-y-3">
            <h2 className="text-base sm:text-lg font-bold font-display text-spice-black flex items-center gap-2">
              <FileText className="h-5 w-5 text-saffron-600" />
              <span>1. Identification of Seller</span>
            </h2>
            <p>
              This website is operated by <strong className="text-spice-black font-semibold">Bharat Masala Products Private Limited</strong>, a company incorporated under the laws of India, having its primary manufacturing and packaging operations at B.H. Road, Thirthahalli, Shimoga District, Karnataka — 577432.
            </p>
          </section>

          <section className="space-y-3 pt-6 border-t border-spice-borderSubtle">
            <h2 className="text-base sm:text-lg font-bold font-display text-spice-black flex items-center gap-2">
              <Scale className="h-5 w-5 text-saffron-600" />
              <span>2. Pricing, Taxes &amp; GST Invoicing</span>
            </h2>
            <p>
              All prices displayed across the retail catalog are inclusive of applicable Indian Goods and Services Tax (GST: 5% on pure ground/whole spices, 12% on specific processed blends).
            </p>
            <p>
              Upon successful payment settlement, an authoritative electronic GST Tax Invoice displaying our statutory GSTIN, HSN classification codes, customer billing details, and CGST/SGST/IGST breakdown is automatically generated and archived in your account.
            </p>
          </section>

          <section className="space-y-3 pt-6 border-t border-spice-borderSubtle">
            <h2 className="text-base sm:text-lg font-bold font-display text-spice-black flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-saffron-600" />
              <span>3. Legal Metrology Compliance</span>
            </h2>
            <p>
              In accordance with the Legal Metrology (Packaged Commodities) Rules, 2011, every package clearly declares the net weight, date of manufacture/packing, best before date, Maximum Retail Price (inclusive of all taxes), country of origin, and registered contact information of the manufacturer.
            </p>
          </section>

          <section className="space-y-3 pt-6 border-t border-spice-borderSubtle">
            <h2 className="text-base sm:text-lg font-bold font-display text-spice-black flex items-center gap-2">
              <Scale className="h-5 w-5 text-saffron-600" />
              <span>4. Governing Law &amp; Dispute Resolution</span>
            </h2>
            <p>
              These Terms shall be governed and construed in accordance with the laws of the Republic of India. Any legal dispute or claim arising out of or related to our products or services shall be subject to the exclusive jurisdiction of the competent courts in Shimoga, Karnataka.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
