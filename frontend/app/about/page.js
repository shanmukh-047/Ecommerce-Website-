'use client';

import React from 'react';
import Link from 'next/link';
import {
  ShieldCheck,
  Sparkles,
  Award,
  HeartHandshake,
  ArrowRight,
  CheckCircle2,
  TreePine,
  ThermometerSnowflake,
  Scale,
} from 'lucide-react';
import Button from '../../components/common/Button';

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-spice-canvas">
      {/* Hero Banner */}
      <section className="relative py-16 sm:py-24 bg-gradient-to-b from-stone-900 via-spice-earth to-stone-900 text-white overflow-hidden">
        <div className="absolute inset-0 opacity-10 bg-[radial-gradient(#C05621_1px,transparent_1px)] [background-size:16px_16px]" />
        
        <div className="relative max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center space-y-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-saffron-600/30 border border-saffron-400/30 text-xs font-semibold text-saffron-300">
            <Sparkles className="h-3.5 w-3.5 text-saffron-400" />
            <span>Single-Origin Western Ghats Terroir</span>
          </div>

          <h1 className="text-3xl sm:text-5xl lg:text-6xl font-display font-extrabold tracking-tight text-white leading-tight">
            Pure Estate Spices from the <br className="hidden sm:inline" />
            <span className="text-saffron-400 italic">Misty Slopes of Malenadu</span>
          </h1>

          <p className="text-sm sm:text-base text-stone-300 max-w-2xl mx-auto leading-relaxed">
            Since 1984, Bharat Masala has partnered with smallholder family planters in Thirthahalli, Wayanad, and Idukki to bring you hand-harvested, non-irradiated, cryogenic cold-milled spices that preserve nature’s volatile essential oils.
          </p>
        </div>
      </section>

      {/* Core Values Strip */}
      <section className="py-12 bg-white border-b border-spice-borderSubtle">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
            <div className="flex items-start gap-4">
              <div className="h-10 w-10 rounded-xl bg-saffron-50 text-saffron-700 flex items-center justify-center shrink-0 border border-saffron-200">
                <TreePine className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-spice-black font-display">100% Single Origin</h3>
                <p className="text-xs text-spice-stone mt-1 leading-relaxed">
                  Traceable to individual estate valleys in Karnataka and Kerala. Never blended with bulk industrial lots.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-4">
              <div className="h-10 w-10 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center shrink-0 border border-emerald-200">
                <ThermometerSnowflake className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-spice-black font-display">Cold Milling &lt;38°C</h3>
                <p className="text-xs text-spice-stone mt-1 leading-relaxed">
                  Slow stone and cryogenic milling prevents heat degradation, locking in the aromatic piperine and curcumin.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-4">
              <div className="h-10 w-10 rounded-xl bg-amber-50 text-amber-700 flex items-center justify-center shrink-0 border border-amber-200">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-spice-black font-display">FSSAI Certified Pure</h3>
                <p className="text-xs text-spice-stone mt-1 leading-relaxed">
                  Zero artificial colors, zero synthetic preservatives, and zero starch fillers. Guaranteed unadulterated.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-4">
              <div className="h-10 w-10 rounded-xl bg-stone-100 text-stone-700 flex items-center justify-center shrink-0 border border-stone-200">
                <HeartHandshake className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-spice-black font-display">Fair Direct Sourcing</h3>
                <p className="text-xs text-spice-stone mt-1 leading-relaxed">
                  We bypass auction intermediaries, paying our estate growers 20–30% above standard mandi market rates.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Terroir Sourcing Story */}
      <section className="py-16 sm:py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center">
            <div className="space-y-6">
              <div className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-saffron-700">
                <Scale className="h-4 w-4" />
                <span>Our Heritage &amp; Soil</span>
              </div>

              <h2 className="text-2xl sm:text-4xl font-display font-bold text-spice-black leading-tight">
                Where High Humidity, Ancient Laterite Soil, and Canopy Shade Meet.
              </h2>

              <p className="text-sm text-spice-stone leading-relaxed">
                The Western Ghats of India are one of the world’s eight &ldquo;hottest hotspots&rdquo; of biological diversity. Nestled between the Tunga river basin and the Arabian Sea escarpment, our partner plantations thrive under natural evergreen tree canopies.
              </p>

              <p className="text-sm text-spice-stone leading-relaxed">
                This unique micro-climate produces Tellicherry Black Pepper with high essential oil density (550GL+ bulk density), Wayanad Cardamom with bold 8mm+ pods bursting with aromatic cineole, and Salem Turmeric with high natural curcumin percentages (4.5%+).
              </p>

              <div className="space-y-3 pt-2">
                <div className="flex items-center gap-3 text-xs font-semibold text-spice-black">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
                  <span>Hand-sorted and sun-dried on clean bamboo raised beds</span>
                </div>
                <div className="flex items-center gap-3 text-xs font-semibold text-spice-black">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
                  <span>Nitrogen-flushed multi-layer pouches to seal peak harvest freshness</span>
                </div>
                <div className="flex items-center gap-3 text-xs font-semibold text-spice-black">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
                  <span>Strict Legal Metrology compliance and statutory batch testing</span>
                </div>
              </div>

              <div className="pt-4 flex flex-wrap items-center gap-4">
                <Link href="/products">
                  <Button variant="primary" size="md" rightIcon={<ArrowRight className="h-4 w-4" />}>
                    Explore Our Spices
                  </Button>
                </Link>
                <Link href="/wholesale">
                  <Button variant="outline-stone" size="md">
                    B2B Wholesale Procurement
                  </Button>
                </Link>
              </div>
            </div>

            {/* Terroir Card Display */}
            <div className="rounded-3xl p-8 sm:p-10 bg-gradient-to-br from-amber-50 via-orange-50 to-stone-100 border border-saffron-200 shadow-sm space-y-6">
              <div className="flex items-center justify-between border-b border-saffron-200/60 pb-4">
                <div>
                  <h4 className="text-base font-bold font-display text-spice-black">Sharada’s Oral Culinary Wisdom</h4>
                  <p className="text-xs text-spice-muted">Passed through generations of Malenadu cooks</p>
                </div>
                <Award className="h-6 w-6 text-saffron-600" />
              </div>

              <blockquote className="text-sm text-spice-stone italic leading-relaxed border-l-2 border-saffron-500 pl-4">
                &ldquo;Do not roast green cardamom on high flame; its sweetness evaporates into the smoke. Gently crush it as your gravy rests. Let the steam do the work.&rdquo;
              </blockquote>

              <div className="grid grid-cols-2 gap-4 pt-4 text-xs">
                <div className="p-3.5 rounded-xl bg-white/80 border border-saffron-100">
                  <span className="text-[11px] text-spice-muted block">Central Operations</span>
                  <span className="font-bold text-spice-black mt-0.5 block">Thirthahalli, Karnataka</span>
                </div>
                <div className="p-3.5 rounded-xl bg-white/80 border border-saffron-100">
                  <span className="text-[11px] text-spice-muted block">FSSAI Central License</span>
                  <span className="font-mono font-bold text-spice-black mt-0.5 block">11223344556677</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
