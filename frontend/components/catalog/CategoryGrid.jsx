'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { ArrowRight, ShieldCheck, Sparkles, Flame, Sprout } from 'lucide-react';
import catalogService from '../../services/catalogService';
import Skeleton from '../common/Skeleton';

const CATEGORY_ICONS = {
  'pure-spices': ShieldCheck,
  'ground-spices': Flame,
  'signature-blends': Sparkles,
  'dry-fruits': Sprout,
};

export default function CategoryGrid() {
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
      <section className="py-12 bg-white border-b border-spice-borderSubtle">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-8">
            <Skeleton height="14px" width="120px" className="mx-auto mb-2" />
            <Skeleton height="28px" width="280px" className="mx-auto" />
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} height="140px" className="rounded-2xl" />
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
        <div className="flex flex-col sm:flex-row items-center justify-between mb-8 gap-3">
          <div>
            <span className="text-xs font-bold uppercase tracking-widest text-saffron-700 block mb-1">
              Curated Collections
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold font-display text-spice-black tracking-tight">
              Explore by Spice Category
            </h2>
          </div>
          <Link
            href="/products"
            className="inline-flex items-center gap-1.5 text-xs font-bold text-saffron-700 hover:text-saffron-800 uppercase tracking-wider group"
          >
            <span>View All Spices</span>
            <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-1" />
          </Link>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {categories.map((category) => {
            const Icon = CATEGORY_ICONS[category.slug] || Sparkles;
            return (
              <Link
                key={category.id || category.slug}
                href={`/products?category=${category.slug}`}
                className="group relative flex flex-col justify-between p-5 rounded-2xl bg-spice-canvas/80 border border-spice-border hover:border-saffron-500 hover:shadow-card-hover transition-all duration-200"
              >
                <div>
                  <div className="h-12 w-12 rounded-xl bg-white border border-spice-borderSubtle flex items-center justify-center text-saffron-700 mb-4 shadow-2xs group-hover:bg-saffron-600 group-hover:text-white transition-colors">
                    <Icon className="h-6 w-6" />
                  </div>
                  <h3 className="text-sm sm:text-base font-bold text-spice-black mb-1.5 group-hover:text-saffron-700 transition-colors">
                    {category.name}
                  </h3>
                  {category.description && (
                    <p className="text-xs text-spice-stone line-clamp-2 leading-relaxed">
                      {category.description}
                    </p>
                  )}
                </div>

                <div className="mt-4 pt-3 border-t border-spice-borderSubtle/60 flex items-center justify-between text-xs font-semibold text-saffron-700">
                  <span>Browse Range</span>
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
