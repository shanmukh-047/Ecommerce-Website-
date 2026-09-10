'use client';

import React from 'react';
import { ShieldCheck, Sparkles, MapPin, Scale, Leaf, Clock } from 'lucide-react';

const REASONS = [
  {
    icon: MapPin,
    title: 'Single-Origin Estate Terroir',
    description:
      'Harvested exclusively from rain-fed valleys in Malenadu (Shimoga), Wayanad, and Idukki. Every pod and berry carries the unique mineral soil profile of the Western Ghats.',
    badge: 'Origin Traced',
    color: 'text-amber-700 bg-amber-50',
  },
  {
    icon: Sparkles,
    title: 'Slow Cold-Milling (<38°C)',
    description:
      'Industrial mills generate friction heat over 70°C that scorches essential oils. Our proprietary slow-milling keeps temperatures below 38°C, locking in authentic aroma.',
    badge: 'Aroma Retained',
    color: 'text-saffron-700 bg-saffron-50',
  },
  {
    icon: ShieldCheck,
    title: 'Zero Fillers, Zero Adulteration',
    description:
      'Never diluted with spent spice dust, starches, artificial dyes, or anti-caking agents. What you receive is 100% pure, unblemished spice as nature intended.',
    badge: '100% Pure',
    color: 'text-emerald-700 bg-emerald-50',
  },
  {
    icon: Scale,
    title: 'FSSAI & Statutory Metrology',
    description:
      'Batch-tested in certified laboratories for moisture content, active curcumin %, piperine levels, aflatoxins, and heavy metals before packaging.',
    badge: 'Lab Tested',
    color: 'text-blue-700 bg-blue-50',
  },
  {
    icon: Clock,
    title: 'Milled Fresh in Small Batches',
    description:
      'We never store months of pre-ground powder in humid warehouses. Spices are milled in small weekly batches at our Thirthahalli mill and shipped within days.',
    badge: 'Small Batches',
    color: 'text-purple-700 bg-purple-50',
  },
  {
    icon: Leaf,
    title: 'Fair Farmer Partnerships',
    description:
      'By cutting out speculative middlemen, we pay premium rates directly to generational growers who practice shade-grown, biodiverse polyculture.',
    badge: 'Direct Trade',
    color: 'text-cardamom-700 bg-cardamom-50',
  },
];

export default function WhyChooseUs() {
  return (
    <section className="py-20 bg-spice-canvas border-b border-spice-borderSubtle">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <span className="text-xs font-bold uppercase tracking-widest text-saffron-700 block mb-2">
            The Estate Difference
          </span>
          <h2 className="text-3xl sm:text-4xl font-bold font-display text-spice-black tracking-tight mb-4">
            Why Discerning Kitchens Choose Bharat Masala
          </h2>
          <p className="text-sm sm:text-base text-spice-stone leading-relaxed">
            In an era of mass-market spice adulteration and stale industrial powders, we preserve
            traditional Malenadu agro-forestry and heritage milling practices.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {REASONS.map((reason, idx) => {
            const Icon = reason.icon;
            return (
              <div
                key={idx}
                className="group relative flex flex-col justify-between p-6 sm:p-7 rounded-2xl bg-white border border-spice-border hover:border-saffron-500/60 hover:shadow-card-hover transition-all duration-200"
              >
                <div>
                  <div className="flex items-center justify-between mb-5">
                    <div className={`h-12 w-12 rounded-xl ${reason.color} flex items-center justify-center shadow-2xs group-hover:scale-105 transition-transform`}>
                      <Icon className="h-6 w-6" />
                    </div>
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full bg-spice-canvas border border-spice-borderSubtle text-spice-stone">
                      {reason.badge}
                    </span>
                  </div>

                  <h3 className="text-base font-bold text-spice-black mb-2.5 group-hover:text-saffron-700 transition-colors">
                    {reason.title}
                  </h3>

                  <p className="text-xs sm:text-sm text-spice-stone leading-relaxed">
                    {reason.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
