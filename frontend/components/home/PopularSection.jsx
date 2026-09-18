'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { ArrowRight, Flame, Sparkles } from 'lucide-react';
import catalogService from '../../services/catalogService';
import ProductCard from '../common/ProductCard';
import { ProductCardSkeleton } from '../common/Skeleton';

export default function PopularSection() {
  const [products, setProducts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    async function load() {
      try {
        const data = await catalogService.getBestsellerProducts({ page_size: 8 });
        if (isMounted) {
          setProducts(data?.results || []);
        }
      } catch (err) {
        console.error('Failed to load popular spices:', err);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }
    load();
    return () => {
      isMounted = false;
    };
  }, []);

  if (!isLoading && products.length === 0) return null;

  return (
    <section className="py-16 bg-white border-b border-spice-borderSubtle">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col sm:flex-row items-start sm:items-end justify-between mb-8 gap-4">
          <div>
            <div className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 border border-amber-200/80 px-3 py-1 text-xs font-semibold text-amber-900 mb-2">
              <Flame className="h-3.5 w-3.5 text-amber-600" />
              <span>Customer Staples</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold font-display text-spice-black tracking-tight">
              Most Loved Across Indian Kitchens
            </h2>
            <p className="mt-1 text-xs sm:text-sm text-spice-stone">
              The everyday staples and signature blends that define Bharat Masala’s uncompromising quality.
            </p>
          </div>

          <Link
            href="/products?bestseller=true"
            className="inline-flex items-center gap-1.5 text-xs font-bold text-saffron-700 hover:text-saffron-800 uppercase tracking-wider group shrink-0"
          >
            <span>View All Bestsellers</span>
            <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-1" />
          </Link>
        </div>

        {/* Products Grid */}
        {isLoading ? (
          <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-6">
            {Array.from({ length: 4 }).map((_, i) => (
              <ProductCardSkeleton key={i} />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-6">
            {products.map((product) => (
              <ProductCard key={product.id || product.slug} product={product} />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
