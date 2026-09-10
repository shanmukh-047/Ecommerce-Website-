'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { ArrowRight, Sparkles, Award } from 'lucide-react';
import catalogService from '../../services/catalogService';
import ProductCard from '../common/ProductCard';
import { ProductCardSkeleton } from '../common/Skeleton';

export default function FeaturedSpices() {
  const [products, setProducts] = useState([]);
  const [filter, setFilter] = useState('ALL');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    async function load() {
      setIsLoading(true);
      try {
        const params = { page_size: 8 };
        if (filter === 'RESERVE') params.tier = 'RESERVE';
        if (filter === 'PURE') params.category = 'pure-spices';

        const data = await catalogService.getProducts(params);
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
  }, [filter]);

  return (
    <section className="py-16 bg-spice-canvas">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-8 gap-4">
          <div>
            <div className="inline-flex items-center gap-1.5 rounded-full bg-saffron-50 border border-saffron-200/80 px-3 py-1 text-xs font-semibold text-saffron-800 mb-2">
              <Award className="h-3.5 w-3.5 text-saffron-700" />
              <span>Direct Estate Harvests</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold font-display text-spice-black tracking-tight">
              Featured Western Ghats Spices
            </h2>
            <p className="mt-1 text-sm text-spice-stone">
              Hand-graded for volatile oil potency, aroma, and natural terroir.
            </p>
          </div>

          {/* Filter Pills */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
            <button
              type="button"
              onClick={() => setFilter('ALL')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                filter === 'ALL'
                  ? 'bg-saffron-600 text-white shadow-2xs'
                  : 'bg-white border border-spice-border text-spice-stone hover:bg-spice-canvas'
              }`}
            >
              All Harvests
            </button>
            <button
              type="button"
              onClick={() => setFilter('RESERVE')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5 ${
                filter === 'RESERVE'
                  ? 'bg-amber-950 text-amber-200 shadow-2xs'
                  : 'bg-white border border-spice-border text-spice-stone hover:bg-spice-canvas'
              }`}
            >
              <Sparkles className="h-3 w-3 text-amber-500" />
              <span>Reserve Grade</span>
            </button>
            <button
              type="button"
              onClick={() => setFilter('PURE')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                filter === 'PURE'
                  ? 'bg-saffron-600 text-white shadow-2xs'
                  : 'bg-white border border-spice-border text-spice-stone hover:bg-spice-canvas'
              }`}
            >
              Pure Whole Spices
            </button>
          </div>
        </div>

        {/* Product Cards Grid */}
        {isLoading ? (
          <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
            {Array.from({ length: 4 }).map((_, i) => (
              <ProductCardSkeleton key={i} />
            ))}
          </div>
        ) : products.length > 0 ? (
          <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
            {products.slice(0, 4).map((product) => (
              <ProductCard key={product.id || product.slug} product={product} />
            ))}
          </div>
        ) : (
          <div className="text-center py-12 text-sm text-spice-stone">
            No spices currently featured in this selection.
          </div>
        )}

        {/* View Entire Collection CTA */}
        <div className="mt-10 text-center">
          <Link
            href="/products"
            className="inline-flex items-center gap-2 rounded-xl bg-spice-earth px-6 py-3 text-xs font-bold uppercase tracking-wider text-white shadow-sm hover:bg-spice-black transition-colors"
          >
            <span>Explore All 12 Single-Origin Spices</span>
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </section>
  );
}
