'use client';

import React from 'react';
import Link from 'next/link';
import { ArrowRight, Truck, Sparkles, Building2 } from 'lucide-react';

export default function HomeCTA() {
  return (
    <section className="py-20 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="relative rounded-3xl bg-gradient-to-r from-saffron-700 via-saffron-600 to-amber-700 text-white p-8 sm:p-14 overflow-hidden shadow-xl">
          {/* Decorative radial overlay */}
          <div
            className="absolute inset-0 opacity-10 pointer-events-none"
            style={{
              backgroundImage:
                'radial-gradient(circle at 20% 50%, white 0%, transparent 60%), radial-gradient(circle at 80% 50%, white 0%, transparent 60%)',
            }}
          />

          <div className="relative z-10 max-w-3xl mx-auto text-center">
            {/* Tag */}
            <div className="inline-flex items-center gap-2 rounded-full bg-white/15 border border-white/25 px-4 py-1.5 text-xs font-semibold text-white mb-6 backdrop-blur-xs">
              <Sparkles className="h-3.5 w-3.5 text-amber-200" />
              <span>Estate Harvests Dispatched Daily</span>
            </div>

            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold font-display tracking-tight text-white leading-tight mb-5">
              Experience the Aroma of Freshly Milled Spices Today
            </h2>

            <p className="text-sm sm:text-base text-amber-100/90 leading-relaxed mb-8 max-w-2xl mx-auto font-normal">
              Order direct from Western Ghats estates. Enjoy free tracked shipping across India on all orders over ₹499.
            </p>

            {/* CTAs */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3.5 mb-10">
              <Link
                href="/products"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2.5 rounded-xl bg-white px-8 py-3.5 text-xs font-bold uppercase tracking-wider text-saffron-900 shadow-md hover:bg-amber-50 transition-all active:scale-[0.98]"
              >
                <span>Shop All Spices</span>
                <ArrowRight className="h-4 w-4 text-saffron-800" />
              </Link>

              <Link
                href="/register"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl bg-saffron-900/40 border border-white/30 px-7 py-3.5 text-xs font-bold uppercase tracking-wider text-white hover:bg-saffron-900/60 transition-colors backdrop-blur-xs"
              >
                <Building2 className="h-4 w-4" />
                <span>Wholesale &amp; Bulk Inquiry</span>
              </Link>
            </div>

            {/* Free shipping banner */}
            <div className="inline-flex items-center gap-2 text-xs font-medium text-amber-100/80">
              <Truck className="h-4 w-4 text-amber-200" />
              <span>Standard Tracked Delivery: ₹50 flat, or waived completely on orders ₹499+</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
