'use client';

import React from 'react';
import Link from 'next/link';
import { ArrowRight, BookOpen, Volume2, Sparkles, Heart } from 'lucide-react';

export default function Storytelling() {
  return (
    <section className="py-20 bg-spice-canvas border-b border-spice-borderSubtle overflow-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-16 items-center">
          {/* Left Visual Column */}
          <div className="lg:col-span-5 relative">
            <div className="relative rounded-3xl overflow-hidden bg-gradient-to-br from-amber-100 via-saffron-50 to-orange-100 border border-saffron-200/80 p-8 sm:p-10 shadow-lg text-center">
              {/* Terroir Stamp */}
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/90 border border-saffron-200 text-xs font-bold text-saffron-800 mb-6 shadow-2xs">
                <Sparkles className="h-3.5 w-3.5 text-amber-600" />
                <span>Malenadu Heritage · Est. 1984</span>
              </div>

              {/* Decorative Terroir Emblem */}
              <div className="mx-auto w-28 h-28 sm:w-36 sm:h-36 rounded-full bg-gradient-to-tr from-saffron-600 to-amber-500 flex items-center justify-center text-white shadow-saffron-glow mb-6">
                <div className="text-center">
                  <span className="block font-display text-2xl sm:text-3xl font-extrabold tracking-tight">
                    BM
                  </span>
                  <span className="text-[10px] uppercase font-bold tracking-widest text-amber-100">
                    Estates
                  </span>
                </div>
              </div>

              <h3 className="text-lg sm:text-xl font-bold font-display text-spice-black mb-2">
                Sharada’s Oral Culinary Folklore
              </h3>
              <p className="text-xs sm:text-sm text-spice-stone leading-relaxed mb-6">
                &ldquo;A true masala is not just heat; it is balance. The cumin awakens the palate, the coriander harmonizes, and the hand-picked cardamom lingers like a melody.&rdquo;
              </p>

              {/* Stat Counters */}
              <div className="grid grid-cols-3 gap-3 border-t border-saffron-200/60 pt-6">
                <div>
                  <p className="text-xl sm:text-2xl font-bold font-display text-saffron-800">40+</p>
                  <p className="text-[10px] uppercase tracking-wider font-semibold text-spice-stone mt-0.5">
                    Years Heritage
                  </p>
                </div>
                <div>
                  <p className="text-xl sm:text-2xl font-bold font-display text-saffron-800">100%</p>
                  <p className="text-[10px] uppercase tracking-wider font-semibold text-spice-stone mt-0.5">
                    Single Origin
                  </p>
                </div>
                <div>
                  <p className="text-xl sm:text-2xl font-bold font-display text-saffron-800">&lt;38°C</p>
                  <p className="text-[10px] uppercase tracking-wider font-semibold text-spice-stone mt-0.5">
                    Cold Milling
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Right Text Column */}
          <div className="lg:col-span-7 flex flex-col justify-center">
            <div className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-saffron-700 mb-3">
              <BookOpen className="h-4 w-4" />
              <span>Terroir &amp; Tradition</span>
            </div>

            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold font-display text-spice-black tracking-tight leading-tight mb-6">
              Born from the Mist-Covered Hills of the Western Ghats
            </h2>

            <div className="space-y-4 text-sm sm:text-base text-spice-stone leading-relaxed mb-8">
              <p>
                In the rain-drenched valleys of Thirthahalli along the Tunga river, spice cultivation is not an industry—it is a familial craft passed down through generations. The high humidity, mineral-rich red laterite soil, and canopy shade create the perfect sanctuary for black pepper and cardamom.
              </p>
              <p>
                For decades, our matriarch <strong>Sharada</strong> perfected each blend by sun-drying harvests on estate terraces, slow-roasting them over cast-iron kadai, and stone-pounding them to preserve their fragrant volatile oils.
              </p>
              <p>
                Today, Bharat Masala honors that exact artisanal philosophy. We partner directly with generational growers across Shimoga, Wayanad, and Idukki to ensure that what reaches your home kitchen is authentic, potent, and untouched by industrial shortcuts.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-4">
              <Link
                href="/products?category=signature-blends"
                className="inline-flex items-center gap-2 rounded-xl bg-saffron-600 px-6 py-3 text-xs font-bold uppercase tracking-wider text-white shadow-md hover:bg-saffron-700 transition-all active:scale-[0.98]"
              >
                <span>Discover Signature Blends</span>
                <ArrowRight className="h-4 w-4" />
              </Link>

              <Link
                href="/products"
                className="inline-flex items-center gap-2 rounded-xl bg-white border border-spice-border px-6 py-3 text-xs font-bold uppercase tracking-wider text-spice-black hover:border-saffron-500 hover:text-saffron-700 transition-colors shadow-2xs"
              >
                <span>Browse All Harvests</span>
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
