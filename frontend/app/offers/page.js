'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { Tag, Sparkles, Copy, Check, ArrowRight, ShieldCheck, Truck } from 'lucide-react';
import Button from '../../components/common/Button';
import Badge from '../../components/common/Badge';
import { useToast } from '../../components/common/Toast';

const OFFERS = [
  {
    code: 'FIRSTSPICE',
    title: 'Welcome Harvest Offer',
    discount: '10% Flat Discount',
    description: 'Valid on your first retail purchase of single-origin spices and cold-milled powders.',
    minSpend: '₹399',
    expires: 'Ongoing 2026',
    badge: 'New Customer',
  },
  {
    code: 'ESTATE499',
    title: 'Free Express Transit',
    discount: 'Free Nationwide Shipping',
    description: 'Automatically applied at checkout on all prepaid orders exceeding ₹499.',
    minSpend: '₹499',
    expires: 'All Year',
    badge: 'Popular',
  },
  {
    code: 'MALABAR20',
    title: 'Reserve Pepper & Cardamom Bundle',
    discount: '₹100 Instant Off',
    description: 'Special seasonal price reduction on Reserve Bold 8mm+ Wayanad Cardamom (250g+).',
    minSpend: '₹899',
    expires: 'Seasonal Harvest',
    badge: 'Reserve Tier',
  },
];

export default function OffersPage() {
  const { success } = useToast();
  const [copiedCode, setCopiedCode] = useState(null);

  const handleCopy = (code) => {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(code);
      setCopiedCode(code);
      success(`Coupon code ${code} copied to clipboard!`, 'Coupon Copied');
      setTimeout(() => setCopiedCode(null), 3000);
    }
  };

  return (
    <div className="min-h-screen bg-spice-canvas py-12 sm:py-16">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 space-y-10">
        <div className="text-center space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-saffron-100 text-xs font-semibold text-saffron-800">
            <Tag className="h-3.5 w-3.5" />
            <span>Seasonal Promotions &amp; Coupons</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-display font-extrabold text-spice-black">
            Active Harvest Offers
          </h1>
          <p className="text-xs sm:text-sm text-spice-stone max-w-lg mx-auto">
            Apply these verified coupon codes during checkout to enjoy savings on authentic single-origin estate spices.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {OFFERS.map((offer) => (
            <div
              key={offer.code}
              className="p-6 rounded-3xl bg-white border border-spice-border shadow-xs flex flex-col justify-between space-y-5 hover:border-saffron-300 transition-all"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Badge variant="cardamom" size="xs">
                    {offer.badge}
                  </Badge>
                  <span className="text-[11px] text-spice-muted font-medium">{offer.expires}</span>
                </div>

                <div>
                  <h3 className="text-base font-bold font-display text-spice-black">{offer.title}</h3>
                  <p className="text-sm font-bold text-saffron-700 mt-0.5">{offer.discount}</p>
                </div>

                <p className="text-xs text-spice-stone leading-relaxed">{offer.description}</p>
                <p className="text-[11px] text-spice-muted">Min. Order Value: {offer.minSpend}</p>
              </div>

              <div className="pt-2">
                <div className="p-2.5 rounded-xl bg-spice-canvas border border-dashed border-saffron-300 flex items-center justify-between">
                  <span className="font-mono text-xs font-bold tracking-wider text-spice-black">
                    {offer.code}
                  </span>
                  <button
                    type="button"
                    onClick={() => handleCopy(offer.code)}
                    className="flex items-center gap-1 text-[11px] font-semibold text-saffron-700 hover:text-saffron-800 transition-colors"
                  >
                    {copiedCode === offer.code ? (
                      <>
                        <Check className="h-3.5 w-3.5 text-emerald-600" />
                        <span className="text-emerald-700">Copied!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="h-3.5 w-3.5" />
                        <span>Copy</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="text-center pt-4">
          <Link href="/products">
            <Button variant="primary" size="md" rightIcon={<ArrowRight className="h-4 w-4" />}>
              Shop Eligible Spices Now &rarr;
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
