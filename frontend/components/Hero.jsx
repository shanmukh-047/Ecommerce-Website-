'use client';

import React from 'react';
import Link from 'next/link';
import { ArrowRight, ShieldCheck, Sparkles, MapPin } from 'lucide-react';

export default function Hero() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-spice-canvas via-white to-spice-canvas py-16 sm:py-24 border-b border-spice-borderSubtle">
      {/* Background radial accent */}
      <div
        className="absolute inset-0 pointer-events-none opacity-40"
        style={{
          backgroundImage:
            'radial-gradient(circle at 10% 20%, rgba(200,74,26,0.08), transparent 45%), radial-gradient(circle at 90% 80%, rgba(235,160,55,0.1), transparent 45%)',
        }}
      />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center text-center max-w-3xl mx-auto">
          {/* Provenance Pill */}
          <div className="inline-flex items-center gap-2 rounded-full bg-saffron-50 border border-saffron-200/80 px-3.5 py-1.5 text-xs font-semibold text-saffron-900 mb-6 shadow-2xs">
            <MapPin className="h-3.5 w-3.5 text-saffron-600" />
            <span>Single-Origin Western Ghats Harvests • Karnataka &amp; Kerala</span>
          </div>

          {/* Headline */}
          <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold font-display tracking-tight text-spice-black leading-tight sm:leading-none mb-6">
            Pure Heritage Spices,{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-saffron-600 via-saffron-700 to-amber-700">
              Milled at Source
            </span>
          </h1>

          {/* Subtitle */}
          <p className="text-sm sm:text-base text-spice-stone leading-relaxed mb-8 max-w-2xl">
            Directly sourced from rain-fed estates in Idukki, Coorg, and Shimoga. Zero fillers,
            zero adulteration, and maximum volatile oil retention.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row items-center gap-3 w-full sm:w-auto">
            <Link
              href="/products"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl bg-saffron-600 px-7 py-3.5 text-xs font-bold uppercase tracking-wider text-white shadow-md hover:bg-saffron-700 transition-all active:scale-[0.98]"
            >
              <span>Explore Spice Catalog</span>
              <ArrowRight className="h-4 w-4" />
            </Link>

            <Link
              href="/products?tier=RESERVE"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl bg-white border border-spice-border px-7 py-3.5 text-xs font-bold uppercase tracking-wider text-spice-black hover:border-saffron-500 hover:text-saffron-700 transition-colors shadow-2xs"
            >
              <Sparkles className="h-3.5 w-3.5 text-amber-600" />
              <span>Reserve Collection</span>
            </Link>
          </div>

          {/* Trust Highlights */}
          <div className="mt-12 grid grid-cols-2 sm:grid-cols-3 gap-6 text-left border-t border-spice-borderSubtle pt-8 w-full max-w-2xl">
            <div className="flex items-start gap-2.5">
              <div className="p-1.5 rounded-lg bg-emerald-50 text-emerald-700 shrink-0">
                <ShieldCheck className="h-4 w-4" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-spice-black">FSSAI Certified</h4>
                <p className="text-[11px] text-spice-stone">Licensed quality processing</p>
              </div>
            </div>

            <div className="flex items-start gap-2.5">
              <div className="p-1.5 rounded-lg bg-saffron-50 text-saffron-700 shrink-0">
                <Sparkles className="h-4 w-4" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-spice-black">Cold Ground</h4>
                <p className="text-[11px] text-spice-stone">Aroma &amp; oil preserved</p>
              </div>
            </div>

            <div className="flex items-start gap-2.5 col-span-2 sm:col-span-1">
              <div className="p-1.5 rounded-lg bg-amber-50 text-amber-700 shrink-0">
                <MapPin className="h-4 w-4" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-spice-black">Direct Estate</h4>
                <p className="text-[11px] text-spice-stone">No middlemen markups</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
