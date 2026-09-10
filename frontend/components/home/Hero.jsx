'use client';

import React from 'react';
import Link from 'next/link';
import { ArrowRight, Sparkles, ShieldCheck, Truck, MapPin, Award } from 'lucide-react';

export default function Hero() {
  const quickCategories = [
    { label: 'Pure Whole Spices', href: '/products?category=pure-spices' },
    { label: 'Fresh Ground Powders', href: '/products?category=ground-spices' },
    { label: 'Signature Masalas', href: '/products?category=signature-blends' },
    { label: 'Cashews & Dry Fruits', href: '/products?category=dry-fruits' },
  ];

  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-spice-canvas via-white to-spice-canvas border-b border-spice-borderSubtle py-14 sm:py-20 lg:py-24">
      {/* Background radial glow */}
      <div
        className="absolute inset-0 pointer-events-none opacity-60"
        style={{
          backgroundImage:
            'radial-gradient(circle at 15% 25%, rgba(217, 119, 6, 0.08), transparent 45%), radial-gradient(circle at 85% 75%, rgba(180, 83, 9, 0.08), transparent 45%)',
        }}
      />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center text-center max-w-4xl mx-auto">
          {/* Provenance Pill */}
          <div className="inline-flex items-center gap-2 rounded-full bg-saffron-50 border border-saffron-200/80 px-4 py-1.5 text-xs font-semibold text-saffron-900 mb-6 shadow-2xs">
            <MapPin className="h-3.5 w-3.5 text-saffron-600 shrink-0" />
            <span>Single-Origin Western Ghats Harvests • Karnataka &amp; Kerala</span>
          </div>

          {/* Headline */}
          <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold font-display tracking-tight text-spice-black leading-tight sm:leading-none mb-6">
            Pure Heritage Spices,{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-saffron-600 via-saffron-700 to-amber-700">
              Milled at Source
            </span>
          </h1>

          {/* Subtitle */}
          <p className="text-sm sm:text-base md:text-lg text-spice-stone leading-relaxed mb-8 max-w-2xl font-normal">
            Directly sourced from rain-fed family estates in Thirthahalli, Wayanad, and Idukki.
            Cold-ground below 38°C to seal in intense volatile aroma, natural essential oils, and unmatched flavor.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row items-center gap-3.5 w-full sm:w-auto mb-10">
            <Link
              href="/products"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2.5 rounded-xl bg-saffron-600 px-8 py-3.5 text-xs font-bold uppercase tracking-wider text-white shadow-md hover:bg-saffron-700 transition-all active:scale-[0.98]"
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

          {/* Quick Discovery Chips */}
          <div className="flex flex-wrap items-center justify-center gap-2 mb-12">
            <span className="text-xs font-semibold text-spice-muted mr-1">Quick Browse:</span>
            {quickCategories.map((cat, idx) => (
              <Link
                key={idx}
                href={cat.href}
                className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-white border border-spice-border text-xs font-medium text-spice-stone hover:text-saffron-700 hover:border-saffron-400 hover:bg-saffron-50/50 transition-all shadow-2xs"
              >
                <span>{cat.label}</span>
              </Link>
            ))}
          </div>

          {/* Trust Highlights Strip */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 sm:gap-6 text-left border-t border-spice-borderSubtle pt-8 w-full max-w-4xl">
            <div className="flex items-start gap-3 p-3 rounded-xl bg-white/70 border border-spice-borderSubtle">
              <div className="p-2 rounded-lg bg-emerald-50 text-emerald-700 shrink-0">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-spice-black">FSSAI Certified</h4>
                <p className="text-[11px] text-spice-stone">100% lab-tested &amp; compliant</p>
              </div>
            </div>

            <div className="flex items-start gap-3 p-3 rounded-xl bg-white/70 border border-spice-borderSubtle">
              <div className="p-2 rounded-lg bg-saffron-50 text-saffron-700 shrink-0">
                <Sparkles className="h-5 w-5" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-spice-black">Cold-Ground &lt;38°C</h4>
                <p className="text-[11px] text-spice-stone">Volatile essential oils sealed</p>
              </div>
            </div>

            <div className="flex items-start gap-3 p-3 rounded-xl bg-white/70 border border-spice-borderSubtle">
              <div className="p-2 rounded-lg bg-amber-50 text-amber-700 shrink-0">
                <Award className="h-5 w-5" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-spice-black">Estate Terroir</h4>
                <p className="text-[11px] text-spice-stone">Zero filler, single origin</p>
              </div>
            </div>

            <div className="flex items-start gap-3 p-3 rounded-xl bg-white/70 border border-spice-borderSubtle">
              <div className="p-2 rounded-lg bg-blue-50 text-blue-700 shrink-0">
                <Truck className="h-5 w-5" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-spice-black">Free Shipping ₹499+</h4>
                <p className="text-[11px] text-spice-stone">Tracked transit across India</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
