'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { ArrowRight, ShieldCheck, Flame, Sparkles, Sprout } from 'lucide-react';
import catalogService from '../../services/catalogService';
import Skeleton from '../common/Skeleton';

const CATEGORY_META = {
  'pure-spices': {
    icon: ShieldCheck,
    accent: 'from-amber-500/10 to-saffron-500/10',
    border: 'hover:border-amber-500',
    iconBg: 'bg-amber-100 text-amber-800',
    badge: 'Single Origin Whole',
  },
  'ground-spices': {
    icon: Flame,
    accent: 'from-red-500/10 to-orange-500/10',
    border: 'hover:border-red-500',
    iconBg: 'bg-orange-100 text-orange-800',
    badge: 'Cold Ground <38°C',
  },
  'signature-blends': {
    icon: Sparkles,
    accent: 'from-saffron-500/10 to-amber-500/10',
    border: 'hover:border-saffron-500',
    iconBg: 'bg-saffron-100 text-saffron-800',
    badge: 'Sharada’s Heritage Blends',
  },
  'dry-fruits': {
    icon: Sprout,
    accent: 'from-emerald-500/10 to-teal-500/10',
    border: 'hover:border-emerald-500',
    iconBg: 'bg-emerald-100 text-emerald-800',
    badge: 'Malenadu Estate Harvest',
  },
};

export default function CategorySection() {
  const [categories, setCategories] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    async function load() {
      try {
        const data = await catalogService.getCategories();
        if (isMounted) {
          const list = Array.isArray(data) ? data : data?.results || [];
          setCategories(list);
        }
      } catch (err) {
        console.error('Failed to load categories:', err);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }
    load();
    return () => {
      isMounted = false;
    };
  }, []);

  if (isLoading) {
    return (
      <section className="py-14 bg-white border-b border-spice-borderSubtle">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center mb-8">
            <div>
              <Skeleton height="14px" width="130px" className="mb-2" />
              <Skeleton height="28px" width="260px" />
            </div>
            <Skeleton height="20px" width="110px" />
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5 sm:gap-6">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} height="180px" className="rounded-2xl" />
            ))}
          </div>
        </div>
      </section>
    );
  }

  if (categories.length === 0) return null;

  return (
    <section className="py-14 bg-white border-b border-spice-borderSubtle">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col sm:flex-row items-start sm:items-end justify-between mb-8 gap-4">
          <div>
            <span className="text-xs font-bold uppercase tracking-widest text-saffron-700 block mb-1">
              Curated Collections
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold font-display text-spice-black tracking-tight">
              Explore by Spice Category
            </h2>
            <p className="text-xs sm:text-sm text-spice-stone mt-1">
              From unblemished whole pods to cold-milled masalas, discover genuine Malenadu flavors.
            </p>
          </div>
          <Link
            href="/products"
            className="inline-flex items-center gap-1.5 text-xs font-bold text-saffron-700 hover:text-saffron-800 uppercase tracking-wider group shrink-0"
          >
            <span>View All Spices</span>
            <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-1" />
          </Link>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5 sm:gap-6">
          {categories.map((category) => {
            const meta = CATEGORY_META[category.slug] || {
              icon: Sparkles,
              accent: 'from-saffron-500/10 to-amber-500/10',
              border: 'hover:border-saffron-500',
              iconBg: 'bg-saffron-100 text-saffron-800',
              badge: 'Estate Fresh',
            };
            const Icon = meta.icon;
            const subcount = category.subcategories?.length || 0;

            return (
              <Link
                key={category.id || category.slug}
                href={`/products?category=${category.slug}`}
                className={`group relative flex flex-col justify-between p-3.5 sm:p-6 rounded-2xl bg-gradient-to-br from-spice-canvas/90 to-white border border-spice-border ${meta.border} hover:shadow-card-hover transition-all duration-200 min-w-0`}
              >
                <div>
                  <div className="flex items-center justify-between gap-1.5 flex-wrap mb-3 sm:mb-4">
                    <div className={`h-10 w-10 sm:h-12 sm:w-12 rounded-xl ${meta.iconBg} flex items-center justify-center shadow-2xs group-hover:scale-105 transition-transform shrink-0`}>
                      <Icon className="h-5 w-5 sm:h-6 sm:w-6" />
                    </div>
                    <span className="text-[9px] sm:text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-white border border-spice-border text-spice-stone truncate">
                      {meta.badge}
                    </span>
                  </div>

                  <h3 className="text-sm sm:text-base font-bold text-spice-black mb-1.5 group-hover:text-saffron-700 transition-colors">
                    {category.name}
                  </h3>

                  {category.description ? (
                    <p className="text-xs text-spice-stone line-clamp-2 leading-relaxed">
                      {category.description}
                    </p>
                  ) : (
                    <p className="text-xs text-spice-stone">
                      Pure estate-sourced harvests milled at origin.
                    </p>
                  )}
                </div>

                <div className="mt-5 pt-3 border-t border-spice-borderSubtle flex items-center justify-between text-xs font-semibold text-spice-stone group-hover:text-saffron-700">
                  <span>{subcount > 0 ? `${subcount} Sub-varieties` : 'Shop Collection'}</span>
                  <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-1" />
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </section>
  );
}
