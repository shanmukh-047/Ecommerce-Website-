'use client';

import React from 'react';
import { ShieldCheck, CheckCircle2, FlaskConical, Award, Lock, RefreshCw } from 'lucide-react';

export default function QualityPromise() {
  const guarantees = [
    {
      title: 'Active Phytochemical Potency',
      desc: 'Our Salem Turmeric tests at a certified 5.2%+ natural curcumin; our Malabar Pepper exceeds 5.5% piperine for maximum bioactive absorption.',
      icon: FlaskConical,
    },
    {
      title: 'Triple-Layer Moisture Lock',
      desc: 'Packaged in food-grade, nitrogen-flushed 3-ply barrier pouches to prevent essential oil evaporation and humidity contamination for 12 months.',
      icon: Lock,
    },
    {
      title: 'Comprehensive Lab Audits',
      desc: 'Every single harvest batch is independently screened for pesticide residues, aflatoxins, synthetic colorants, and heavy metals.',
      icon: ShieldCheck,
    },
    {
      title: '100% Freshness Guarantee',
      desc: 'Open your packet. If the fragrance and color do not dramatically outmatch standard commercial store spices, we offer an instant replacement or refund.',
      icon: RefreshCw,
    },
  ];

  return (
    <section className="py-16 bg-white border-b border-spice-borderSubtle overflow-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="rounded-3xl bg-gradient-to-br from-spice-earth to-stone-900 text-white p-8 sm:p-12 lg:p-14 overflow-hidden relative shadow-xl">
          {/* Subtle background glow */}
          <div
            className="absolute -right-20 -bottom-20 w-96 h-96 rounded-full opacity-15 pointer-events-none"
            style={{
              background: 'radial-gradient(circle, #D97706 0%, transparent 70%)',
            }}
          />

          <div className="relative z-10 max-w-3xl mb-12">
            <div className="inline-flex items-center gap-2 rounded-full bg-saffron-500/20 border border-saffron-400/30 px-3.5 py-1 text-xs font-semibold text-saffron-300 mb-4">
              <Award className="h-3.5 w-3.5 text-saffron-400" />
              <span>The Bharat Masala Guarantee</span>
            </div>
            <h2 className="text-2xl sm:text-4xl font-bold font-display tracking-tight text-white mb-4">
              Our Unconditional Quality Promise to Your Kitchen
            </h2>
            <p className="text-sm sm:text-base text-stone-300 leading-relaxed">
              We hold our harvests to strict laboratory standards that exceed conventional statutory requirements.
              When you cook with Bharat Masala, you cook with true estate purity.
            </p>
          </div>

          <div className="relative z-10 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {guarantees.map((item, idx) => {
              const Icon = item.icon;
              return (
                <div
                  key={idx}
                  className="rounded-2xl bg-white/5 border border-white/10 p-6 backdrop-blur-xs flex flex-col justify-between hover:bg-white/10 transition-colors"
                >
                  <div>
                    <div className="h-11 w-11 rounded-xl bg-saffron-500/20 text-saffron-400 flex items-center justify-center mb-4">
                      <Icon className="h-5 w-5" />
                    </div>
                    <h3 className="text-sm font-bold text-white mb-2">{item.title}</h3>
                    <p className="text-xs text-stone-300 leading-relaxed">{item.desc}</p>
                  </div>
                  <div className="mt-4 pt-3 border-t border-white/10 flex items-center gap-1.5 text-[11px] font-semibold text-saffron-300">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    <span>Verified Standard</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
