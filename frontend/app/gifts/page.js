'use client';

import React from 'react';
import Link from 'next/link';
import { Gift, Sparkles, Heart, Award, ArrowRight, ShieldCheck } from 'lucide-react';
import Button from '../../components/common/Button';
import Badge from '../../components/common/Badge';

const GIFT_SETS = [
  {
    title: 'Heritage Brass Masala Dabba',
    subtitle: '7 Handcrafted Brass Spice Compartments + Spoon',
    price: '₹2,499',
    description:
      'Pure heavy-gauge spun brass spice chest, packed with seven single-origin estate spices: Tellicherry Pepper, Wayanad Cardamom, Salem Turmeric, Royal Cumin, Cloves, Star Anise, and Cinnamon.',
    badge: 'Artisanal Heirlooms',
    slug: 'brass-masala-dabba',
  },
  {
    title: 'Malenadu Estate Terroir Trio',
    subtitle: 'Black Pepper, Green Cardamom & Golden Turmeric',
    price: '₹899',
    description:
      'Presented in a bespoke pine-wood sliding box. Three full-size 100g glass jars featuring our highest oil-content estate harvests.',
    badge: 'Bestseller Hamper',
    slug: 'malenadu-terroir-trio',
  },
  {
    title: 'Master Chef Spice Tasting Collection',
    subtitle: '12 Curated Rare Indian Spices & Heirloom Masalas',
    price: '₹1,849',
    description:
      'An expansive culinary journey across the Western Ghats and Deccan plateau, complete with grinding stones and recipe pairing guide.',
    badge: 'Chef’s Edition',
    slug: 'chef-tasting-collection',
  },
];

export default function GiftsPage() {
  return (
    <div className="min-h-screen bg-spice-canvas py-12 sm:py-16">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
        <div className="text-center space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-saffron-100 text-xs font-semibold text-saffron-800">
            <Gift className="h-3.5 w-3.5" />
            <span>Festive &amp; Corporate Hampers</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-display font-extrabold text-spice-black">
            Artisanal Spice Gift Collections
          </h1>
          <p className="text-xs sm:text-sm text-spice-stone max-w-lg mx-auto">
            Thoughtful gifts for epicures, home chefs, and corporate celebrations, crafted with heirloom brass and single-origin estate harvests.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {GIFT_SETS.map((set, idx) => (
            <div
              key={idx}
              className="rounded-3xl p-6 sm:p-8 bg-white border border-spice-border shadow-xs flex flex-col justify-between space-y-6 hover:shadow-subtle transition-all"
            >
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <Badge variant="cardamom" size="xs">
                    {set.badge}
                  </Badge>
                  <span className="text-base font-bold font-display text-spice-black">{set.price}</span>
                </div>

                <div>
                  <h3 className="text-lg font-bold font-display text-spice-black">{set.title}</h3>
                  <p className="text-xs text-saffron-700 font-semibold mt-0.5">{set.subtitle}</p>
                </div>

                <p className="text-xs text-spice-stone leading-relaxed">{set.description}</p>
              </div>

              <div className="pt-2 border-t border-spice-borderSubtle">
                <Link href="/products">
                  <Button variant="primary" size="md" isFullWidth rightIcon={<ArrowRight className="h-4 w-4" />}>
                    View In Catalog &rarr;
                  </Button>
                </Link>
              </div>
            </div>
          ))}
        </div>

        <div className="rounded-3xl p-8 bg-gradient-to-r from-amber-50 to-stone-100 border border-saffron-200 text-center space-y-4">
          <h3 className="text-lg sm:text-xl font-bold font-display text-spice-black">
            Custom Corporate &amp; Wedding Gifting
          </h3>
          <p className="text-xs sm:text-sm text-spice-stone max-w-xl mx-auto leading-relaxed">
            Looking to gift customized single-origin spice chests with company branding, bespoke ribbons, or personalized message scrolls?
          </p>
          <div className="pt-2">
            <Link href="/contact">
              <Button variant="outline-stone" size="md">
                Enquire for Bespoke Corporate Gifting
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
