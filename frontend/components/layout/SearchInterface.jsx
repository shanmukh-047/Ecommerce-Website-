'use client';

import React, { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { Search, X, Loader2, ArrowRight } from 'lucide-react';
import catalogService from '../../services/catalogService';

const POPULAR_SEARCHES = ['Black Pepper', 'Green Cardamom', 'Salem Turmeric', 'Ceylon Cinnamon', 'Star Anise'];

/**
 * Dynamic live search interface for the Header.
 * Supports debounced queries against the Django catalog API, popular tags, and instant suggestions.
 */
export default function SearchInterface({ className = '' }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const searchContainerRef = useRef(null);
  const router = useRouter();

  // Close dropdown on outside click
  useEffect(() => {
    const handleOutside = (e) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutside);
    return () => document.removeEventListener('mousedown', handleOutside);
  }, []);

  // Debounce API search
  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      setIsLoading(false);
      return;
    }

    const timer = setTimeout(async () => {
      setIsLoading(true);
      try {
        const data = await catalogService.searchProducts(query, 5);
        setResults(data?.results || []);
      } catch {
        setResults([]);
      } finally {
        setIsLoading(false);
      }
    }, 280);

    return () => clearTimeout(timer);
  }, [query]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) {
      setIsOpen(false);
      router.push(`/products?search=${encodeURIComponent(query.trim())}`);
    }
  };

  const handleSelectPopular = (term) => {
    setQuery(term);
    setIsOpen(false);
    router.push(`/products?search=${encodeURIComponent(term)}`);
  };

  return (
    <div className={`relative w-full ${className}`} ref={searchContainerRef}>
      <form onSubmit={handleSubmit} className="relative">
        <div className="relative flex items-center">
          <Search
            className="pointer-events-none absolute left-3.5 h-4 w-4 text-spice-muted"
            aria-hidden="true"
          />

          <input
            type="search"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              if (!isOpen) setIsOpen(true);
            }}
            onFocus={() => setIsOpen(true)}
            placeholder="Search spices, seeds, masalas..."
            className="w-full rounded-xl border border-spice-border bg-spice-canvas/80 py-2 pl-10 pr-9 text-xs sm:text-sm text-spice-black placeholder:text-spice-muted/80 transition-all focus:border-saffron-600 focus:bg-white focus:outline-none focus:ring-2 focus:ring-saffron-500/20"
          />

          {isLoading ? (
            <Loader2 className="absolute right-3 h-4 w-4 animate-spin text-spice-muted" />
          ) : query ? (
            <button
              type="button"
              onClick={() => {
                setQuery('');
                setResults([]);
              }}
              className="absolute right-3 text-spice-muted hover:text-spice-black"
              aria-label="Clear search"
            >
              <X className="h-4 w-4" />
            </button>
          ) : null}
        </div>
      </form>

      {/* Live Suggestions & Popular Searches Dropdown */}
      {isOpen && (
        <div className="absolute left-0 right-0 top-full mt-2 rounded-2xl border border-spice-border bg-white shadow-modal overflow-hidden z-50 animate-slideUp">
          {query.trim() ? (
            <div className="p-3">
              <div className="flex items-center justify-between px-2 pb-2 text-[11px] font-bold uppercase tracking-wider text-spice-muted border-b border-spice-borderSubtle">
                <span>Products</span>
                {results.length > 0 && <span>{results.length} found</span>}
              </div>

              {isLoading ? (
                <div className="py-6 text-center text-xs text-spice-muted">
                  Searching Western Ghats spices...
                </div>
              ) : results.length > 0 ? (
                <div className="divide-y divide-spice-borderSubtle">
                  {results.map((product) => {
                    const price = product.starting_price || product.price || product.variants?.[0]?.selling_price;
                    const image = (typeof product.hero_image === 'string' ? product.hero_image : product.hero_image?.image) || product.image_url || product.image || '/images/spices-placeholder.jpg';

                    return (
                      <Link
                        key={product.id || product.slug}
                        href={`/products/${product.slug}`}
                        onClick={() => setIsOpen(false)}
                        className="flex items-center gap-3 p-2 rounded-lg hover:bg-spice-canvas transition-colors group"
                      >
                        <div className="relative h-10 w-10 rounded-md overflow-hidden bg-spice-canvas shrink-0 border border-spice-border">
                          <Image
                            src={image}
                            alt={product.name}
                            fill
                            sizes="40px"
                            className="object-cover"
                          />
                        </div>

                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-semibold text-spice-black truncate group-hover:text-saffron-700">
                            {product.name}
                          </p>
                          <p className="text-[11px] text-spice-stone truncate">
                            {product.origin_region || product.category?.name || 'Pure Spices'}
                          </p>
                        </div>

                        {price && (
                          <span className="text-xs font-bold text-spice-black tabular-nums shrink-0">
                            From ₹{price}
                          </span>
                        )}
                      </Link>
                    );
                  })}

                  <div className="pt-2 px-1">
                    <button
                      type="button"
                      onClick={handleSubmit}
                      className="w-full flex items-center justify-center gap-1.5 py-2 text-xs font-semibold text-saffron-700 hover:text-saffron-800 hover:bg-saffron-50 rounded-lg transition-colors"
                    >
                      <span>View all results for &ldquo;{query}&rdquo;</span>
                      <ArrowRight className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              ) : (
                <div className="py-6 text-center text-xs text-spice-stone">
                  No spices found matching &ldquo;{query}&rdquo;.
                </div>
              )}
            </div>
          ) : (
            <div className="p-4">
              <p className="text-[11px] font-bold uppercase tracking-wider text-spice-muted mb-2.5">
                Popular Searches
              </p>
              <div className="flex flex-wrap gap-2">
                {POPULAR_SEARCHES.map((term) => (
                  <button
                    key={term}
                    type="button"
                    onClick={() => handleSelectPopular(term)}
                    className="rounded-lg bg-spice-canvas border border-spice-borderSubtle px-3 py-1.5 text-xs text-spice-stone hover:border-saffron-500 hover:text-saffron-700 transition-colors"
                  >
                    {term}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
