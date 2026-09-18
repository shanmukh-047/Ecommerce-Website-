'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { ArrowRight, Sparkles, Award } from 'lucide-react';
import catalogService from '../../services/catalogService';
import ProductCard from '../common/ProductCard';
import { ProductCardSkeleton } from '../common/Skeleton';

export default function FeaturedSection() {
  const [products, setProducts] = useState([]);
  const [activeTier, setActiveTier] = useState('ALL');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    async function load() {
      setIsLoading(true);
      try {
        const params = { page_size: 8 };
        if (activeTier === 'RESERVE') params.tier = 'RESERVE';
        if (activeTier === 'EVERYDAY') params.tier = 'EVERYDAY';

        const data = await catalogService.getFeaturedProducts(params);
        if (isMounted) {
          setProducts(data?.results || []);
        }
      } catch (err) {
        console.error('Failed to load featured spices:', err);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }
    load();
    return () => {
      isMounted = false;
    };
  }, [activeTier]);

  return (
    <section className="py-16 bg-spice-canvas border-b border-spice-borderSubtle">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-8 gap-4">
          <div>
            <div className="inline-flex items-center gap-1.5 rounded-full bg-saffron-50 border border-saffron-200/80 px-3 py-1 text-xs font-semibold text-saffron-800 mb-2">
              <Award className="h-3.5 w-3.5 text-saffron-700" />
              <span>Estate Harvest Showcase</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold font-display text-spice-black tracking-tight">
              Featured Single-Origin Harvests
            </h2>
            <p className="mt-1 text-xs sm:text-sm text-spice-stone">
              Hand-graded for volatile oil potency, natural aroma, and unadulterated Western Ghats terroir.
            </p>
          </div>

          {/* Filter Pills */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1">
            <button
              type="button"
              onClick={() => setActiveTier('ALL')}
              className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
                activeTier === 'ALL'
                  ? 'bg-saffron-600 text-white shadow-2xs'
                  : 'bg-white border border-spice-border text-spice-stone hover:bg-spice-canvas'
              }`}
            >
              All Featured
            </button>
            <button
              type="button"
              onClick={() => setActiveTier('RESERVE')}
              className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all flex items-center gap-1.5 ${
                activeTier === 'RESERVE'
                  ? 'bg-amber-950 text-amber-200 shadow-2xs'
                  : 'bg-white border border-spice-border text-spice-stone hover:bg-spice-canvas'
              }`}
            >
              <Sparkles className="h-3.5 w-3.5 text-amber-500" />
              <span>Reserve Grade</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTier('EVERYDAY')}
              className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
                activeTier === 'EVERYDAY'
                  ? 'bg-saffron-600 text-white shadow-2xs'
                  : 'bg-white border border-spice-border text-spice-stone hover:bg-spice-canvas'
              }`}
            >
              Everyday Essentials
            </button>
          </div>
        </div>

        {/* Product Cards Grid */}
        {isLoading ? (
          <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-6">
            {Array.from({ length: 4 }).map((_, i) => (
              <ProductCardSkeleton key={i} />
            ))}
          </div>
        ) : products.length > 0 ? (
          <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-6">
            {products.map((product) => (
              <ProductCard key={product.id || product.slug} product={product} />
            ))}
          </div>
        ) : (
          <div className="text-center py-12 bg-white rounded-2xl border border-spice-border">
            <p className="text-sm text-spice-stone mb-3">No featured spices in this tier right now.</p>
            <Link
              href="/products"
              className="inline-flex items-center gap-2 text-xs font-bold text-saffron-700 hover:text-saffron-800 uppercase tracking-wider"
            >
              <span>Explore All Spices</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        )}

        {/* Bottom Explorer Link */}
        <div className="mt-10 text-center">
          <Link
            href="/products?tier=RESERVE"
            className="inline-flex items-center gap-2 rounded-xl bg-white border border-spice-border px-6 py-3 text-xs font-bold uppercase tracking-wider text-spice-black hover:border-saffron-500 hover:text-saffron-700 transition-colors shadow-2xs"
          >
            <span>View Full Reserve Collection</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </div>
    </section>
  );
}
