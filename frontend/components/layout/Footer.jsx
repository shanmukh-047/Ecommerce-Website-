'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { ShieldCheck, Award, HeartHandshake, CheckCircle2, ArrowRight } from 'lucide-react';
import { useToast } from '../common/Toast';

/**
 * Production Footer component for Bharat Masala.
 * Features terroir pedigree, customer care links, newsletter subscription, and trust badges.
 */
export default function Footer() {
  const [email, setEmail] = useState('');
  const [isSubscribed, setIsSubscribed] = useState(false);
  const { success } = useToast();

  const handleSubscribe = (e) => {
    e.preventDefault();
    if (!email || !email.includes('@')) return;
    setIsSubscribed(true);
    success('Thank you for subscribing to our harvest updates!', 'Subscribed');
    setEmail('');
  };

  return (
    <footer className="bg-spice-earth text-white pt-16 pb-8 border-t border-white/10 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        {/* Trust Badges Strip */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 pb-12 border-b border-white/10 mb-12">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/5 text-saffron-400 shrink-0 border border-white/10">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <h4 className="text-xs font-bold text-white uppercase tracking-wider">100% Pure Origin</h4>
              <p className="text-[11px] text-stone-400 mt-0.5">Unadulterated Western Ghats spices</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/5 text-saffron-400 shrink-0 border border-white/10">
              <Award className="h-5 w-5" />
            </div>
            <div>
              <h4 className="text-xs font-bold text-white uppercase tracking-wider">FSSAI Certified</h4>
              <p className="text-[11px] text-stone-400 mt-0.5">Rigorous lab food safety testing</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/5 text-saffron-400 shrink-0 border border-white/10">
              <HeartHandshake className="h-5 w-5" />
            </div>
            <div>
              <h4 className="text-xs font-bold text-white uppercase tracking-wider">Direct Farmer Sourcing</h4>
              <p className="text-[11px] text-stone-400 mt-0.5">Fair trade prices for smallholders</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/5 text-saffron-400 shrink-0 border border-white/10">
              <CheckCircle2 className="h-5 w-5" />
            </div>
            <div>
              <h4 className="text-xs font-bold text-white uppercase tracking-wider">Aroma-Lock Packaging</h4>
              <p className="text-[11px] text-stone-400 mt-0.5">Nitrogen-flushed multi-layer pouches</p>
            </div>
          </div>
        </div>

        {/* 4 Main Footer Columns */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-10 pb-12 border-b border-white/10">
          {/* Col 1: Brand Story */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 font-display text-2xl font-bold tracking-tight text-white">
              <span className="inline-flex h-7 w-7 items-center justify-center rounded-lg bg-saffron-600 text-white font-serif text-sm">
                B
              </span>
              <span>
                BHARAT <span className="text-saffron-500 font-normal italic">MASALA</span>
              </span>
            </div>
            <p className="text-xs text-stone-400 leading-relaxed">
              Curating India&apos;s finest single-origin estate spices directly from the misty slopes of Thirthahalli, Wayanad, and Idukki. Hand-harvested, sun-dried, and freshly packed.
            </p>
            <div className="text-[11px] text-stone-500 space-y-1">
              <p>FSSAI Central Lic. No: 11223344556677</p>
              <p>Spices Board of India Reg: SB/REG/2026/09</p>
            </div>
          </div>

          {/* Col 2: Spice Collections */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-widest text-saffron-400 mb-4">
              Spice Collections
            </h4>
            <ul className="space-y-2.5 text-xs text-stone-300">
              <li>
                <Link href="/products?category=pure-spices" className="hover:text-saffron-400 transition-colors">
                  Pure Whole Spices (Black Pepper, Cardamom)
                </Link>
              </li>
              <li>
                <Link href="/products?category=ground-spices" className="hover:text-saffron-400 transition-colors">
                  Single-Origin Ground Powders
                </Link>
              </li>
              <li>
                <Link href="/products?category=signature-blends" className="hover:text-saffron-400 transition-colors">
                  Artisanal Masalas &amp; Signature Blends
                </Link>
              </li>
              <li>
                <Link href="/products?tier=RESERVE" className="hover:text-saffron-400 transition-colors">
                  Reserve Estate Harvests (Bold 550GL+)
                </Link>
              </li>
              <li>
                <Link href="/wholesale" className="hover:text-saffron-400 transition-colors font-medium text-saffron-300">
                  Wholesale Bulk Procurement (B2B)
                </Link>
              </li>
            </ul>
          </div>

          {/* Col 3: Customer Care & Policies */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-widest text-saffron-400 mb-4">
              Customer Care &amp; Trust
            </h4>
            <ul className="space-y-2.5 text-xs text-stone-300">
              <li>
                <Link href="/track" className="hover:text-saffron-400 transition-colors font-medium text-saffron-300">
                  Track Consignment (AWB / Courier)
                </Link>
              </li>
              <li>
                <Link href="/account/orders" className="hover:text-saffron-400 transition-colors">
                  My Orders &amp; Receipts
                </Link>
              </li>
              <li>
                <Link href="/shipping-policy" className="hover:text-saffron-400 transition-colors">
                  Shipping &amp; Transit Timelines
                </Link>
              </li>
              <li>
                <Link href="/returns" className="hover:text-saffron-400 transition-colors">
                  Returns, Replacement &amp; Refunds (RMA)
                </Link>
              </li>
              <li>
                <Link href="/terms" className="hover:text-saffron-400 transition-colors">
                  Terms of Service &amp; GST Invoicing
                </Link>
              </li>
              <li>
                <Link href="/privacy" className="hover:text-saffron-400 transition-colors">
                  Privacy &amp; Data Protection
                </Link>
              </li>
              <li>
                <Link href="/contact" className="hover:text-saffron-400 transition-colors">
                  Contact Support &amp; Farm Visits
                </Link>
              </li>
            </ul>
          </div>

          {/* Col 4: Newsletter & Contact */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-widest text-saffron-400 mb-4">
              Harvest Newsletter
            </h4>
            <p className="text-xs text-stone-400 mb-3 leading-relaxed">
              Get notified when seasonal harvests arrive, plus exclusive heirloom spice recipes.
            </p>

            <form onSubmit={handleSubscribe} className="space-y-2">
              <div className="flex rounded-xl overflow-hidden bg-white/10 border border-white/20 focus-within:border-saffron-500">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Enter your email"
                  required
                  className="bg-transparent px-3 py-2 text-xs text-white placeholder:text-stone-400 focus:outline-none flex-1"
                />
                <button
                  type="submit"
                  aria-label="Subscribe to newsletter"
                  className="bg-saffron-600 hover:bg-saffron-700 text-white px-3 py-2 flex items-center justify-center transition-colors"
                >
                  <ArrowRight className="h-4 w-4" />
                </button>
              </div>
              {isSubscribed && (
                <p className="text-[11px] text-emerald-400">
                  You are registered for harvest updates!
                </p>
              )}
            </form>

            <div className="mt-4 pt-3 border-t border-white/10 text-xs text-stone-400">
              <p className="font-semibold text-white">Central Operations:</p>
              <p className="text-[11px] text-stone-400 mt-0.5">
                Bharat Masala Products, B.H. Road, Shimoga, Karnataka, India — 577201
              </p>
            </div>
          </div>
        </div>

        {/* Bottom Copyright & Payments */}
        <div className="pt-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-stone-400">
          <p>
            © {new Date().getFullYear()} Bharat Masala Products Pvt Ltd. All rights reserved.
          </p>

          <div className="flex items-center gap-3 text-[11px] text-stone-400">
            <span>Secure 256-Bit Encrypted Payments:</span>
            <span className="rounded bg-white/10 px-2 py-0.5 text-white font-semibold">UPI</span>
            <span className="rounded bg-white/10 px-2 py-0.5 text-white font-semibold">RuPay</span>
            <span className="rounded bg-white/10 px-2 py-0.5 text-white font-semibold">Visa / MC</span>
            <span className="rounded bg-white/10 px-2 py-0.5 text-white font-semibold">NetBanking</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
