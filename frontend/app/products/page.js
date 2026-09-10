'use client';

import React, { useState, useEffect, useCallback, useMemo, Suspense } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  SlidersHorizontal,
  Search,
  X,
  ChevronRight,
  Sparkles,
  ArrowUpDown,
  RotateCcw,
  Check,
  Filter,
} from 'lucide-react';
import catalogService from '../../services/catalogService';
import ProductCard from '../../components/common/ProductCard';
import { ProductCardSkeleton } from '../../components/common/Skeleton';
import EmptyState from '../../components/common/EmptyState';
import ErrorState from '../../components/common/ErrorState';
import Drawer from '../../components/common/Drawer';
import Button from '../../components/common/Button';
import Badge from '../../components/common/Badge';

/**
 * Filter and sort definitions matching Django backend capabilities
 */
const TIER_OPTIONS = [
  { value: '', label: 'All Tiers' },
  { value: 'RESERVE', label: 'Reserve Heritage' },
  { value: 'EVERYDAY', label: 'Everyday Essentials' },
];

const FORM_OPTIONS = [
  { value: '', label: 'All Forms' },
  { value: 'WHOLE', label: 'Whole Spices' },
  { value: 'GROUND', label: 'Ground Powders' },
  { value: 'BLEND', label: 'Signature Blends' },
  { value: 'RAW', label: 'Estate Raw' },
];

const SORT_OPTIONS = [
  { value: '', label: 'Featured & Newest' },
  { value: 'price_low_to_high', label: 'Price: Low to High' },
  { value: 'price_high_to_low', label: 'Price: High to Low' },
];

function ProductsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // URL query params
  const currentCategory = searchParams.get('category') || '';
  const currentTier = searchParams.get('tier') || '';
  const currentForm = searchParams.get('form') || '';
  const currentSearch = searchParams.get('search') || '';
  const currentOrdering = searchParams.get('ordering') || '';
  const currentPage = parseInt(searchParams.get('page') || '1', 10);

  // Component state
  const [categories, setCategories] = useState([]);
  const [products, setProducts] = useState([]);
  const [pagination, setPagination] = useState({
    count: 0,
    page: 1,
    total_pages: 1,
    next: null,
    previous: null,
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isMobileFilterOpen, setIsMobileFilterOpen] = useState(false);
  const [searchInput, setSearchInput] = useState(currentSearch);

  // Sync search input if URL changes
  useEffect(() => {
    setSearchInput(currentSearch);
  }, [currentSearch]);

  // Count active non-default filters
  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (currentCategory) count++;
    if (currentTier) count++;
    if (currentForm) count++;
    if (currentSearch) count++;
    return count;
  }, [currentCategory, currentTier, currentForm, currentSearch]);

  // Fetch categories on mount
  useEffect(() => {
    let isMounted = true;
    async function loadCategories() {
      try {
        const data = await catalogService.getCategories();
        if (isMounted) {
          const list = Array.isArray(data) ? data : data?.results || [];
          setCategories(list);
        }
      } catch (err) {
        console.error('Failed to load categories:', err);
      }
    }
    loadCategories();
    return () => {
      isMounted = false;
    };
  }, []);

  // Update URL search parameters
  const updateFilters = useCallback(
    (newParams) => {
      const params = new URLSearchParams(searchParams.toString());

      // If page isn't explicitly changed, reset to page 1 on filter changes
      if (!('page' in newParams)) {
        params.delete('page');
      }

      Object.entries(newParams).forEach(([key, value]) => {
        if (value === '' || value === null || value === undefined) {
          params.delete(key);
        } else {
          params.set(key, String(value));
        }
      });

      router.push(`/products?${params.toString()}`);
    },
    [router, searchParams]
  );

  // Reset all filters
  const resetAllFilters = useCallback(() => {
    setSearchInput('');
    router.push('/products');
  }, [router]);

  // Fetch products when query params change
  const fetchProducts = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = {
        page: currentPage,
      };
      if (currentCategory) params.category = currentCategory;
      if (currentTier) params.tier = currentTier;
      if (currentForm) params.form = currentForm;
      if (currentSearch) params.search = currentSearch;
      if (currentOrdering) params.ordering = currentOrdering;

      const data = await catalogService.getProducts(params);

      if (data) {
        setProducts(data.results || []);
        setPagination({
          count: data.count || 0,
          page: data.page || currentPage,
          total_pages: data.total_pages || 1,
          next: data.next,
          previous: data.previous,
        });
      }
    } catch (err) {
      console.error('Failed to fetch products:', err);
      setError(err.message || 'Unable to retrieve spices from the estate repository.');
    } finally {
      setIsLoading(false);
    }
  }, [currentCategory, currentTier, currentForm, currentSearch, currentOrdering, currentPage]);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  // Handle live search submit
  const handleSearchSubmit = (e) => {
    e.preventDefault();
    updateFilters({ search: searchInput.trim() });
  };

  // Find active category object for title display
  const activeCategoryObj = useMemo(() => {
    if (!currentCategory) return null;
    return categories.find((c) => c.slug === currentCategory);
  }, [categories, currentCategory]);

  return (
    <div className="min-h-screen bg-spice-canvas pb-16 pt-4 sm:pt-6">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Breadcrumb Header */}
        <nav aria-label="Breadcrumb" className="mb-4 flex items-center text-xs text-spice-stone">
          <Link href="/" className="hover:text-saffron-700 transition-colors">
            Home
          </Link>
          <ChevronRight className="mx-1.5 h-3.5 w-3.5 text-spice-muted" />
          <Link
            href="/products"
            className={!currentCategory ? 'font-semibold text-spice-black' : 'hover:text-saffron-700 transition-colors'}
          >
            Spices & Pantry
          </Link>
          {activeCategoryObj && (
            <>
              <ChevronRight className="mx-1.5 h-3.5 w-3.5 text-spice-muted" />
              <span className="font-semibold text-spice-black truncate">{activeCategoryObj.name}</span>
            </>
          )}
        </nav>

        {/* Page Banner & Headline */}
        <div className="mb-6 flex flex-col gap-2 border-b border-spice-borderSubtle pb-5 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-spice-black font-display sm:text-3xl">
              {activeCategoryObj ? activeCategoryObj.name : 'Authentic Western Ghats Spices'}
            </h1>
            <p className="mt-1 text-sm text-spice-stone max-w-2xl">
              {activeCategoryObj?.description ||
                'Estate-harvested, single-origin whole spices, cold-ground masalas, and traditional kitchen blends.'}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-spice-muted">
              {!isLoading && (
                <>
                  Showing <strong className="text-spice-black">{products.length}</strong> of{' '}
                  <strong className="text-spice-black">{pagination.count}</strong> items
                </>
              )}
            </span>
          </div>
        </div>

        {/* Filter Pills & Controls Bar */}
        <div className="mb-6 flex flex-col gap-3 rounded-xl bg-white p-3.5 shadow-subtle border border-spice-border md:flex-row md:items-center md:justify-between">
          {/* Search within catalog */}
          <form onSubmit={handleSearchSubmit} className="relative flex-1 max-w-md">
            <input
              type="text"
              placeholder="Search cardamom, pepper, deggi chilli..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="w-full rounded-lg border border-spice-border bg-spice-canvas/60 py-2 pl-9 pr-9 text-sm text-spice-black placeholder-spice-muted focus:border-saffron-600 focus:bg-white focus:outline-none focus:ring-2 focus:ring-saffron-500/20"
            />
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-spice-muted" />
            {searchInput && (
              <button
                type="button"
                onClick={() => {
                  setSearchInput('');
                  updateFilters({ search: '' });
                }}
                className="absolute right-2.5 top-2.5 text-spice-muted hover:text-spice-black"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </form>

          {/* Right Controls: Sort Dropdown & Mobile Filter Drawer Button */}
          <div className="flex items-center gap-2 justify-between md:justify-end">
            {/* Mobile Filter Toggle */}
            <button
              type="button"
              onClick={() => setIsMobileFilterOpen(true)}
              className="inline-flex items-center gap-2 rounded-lg border border-spice-border bg-white px-3 py-2 text-xs font-semibold text-spice-black hover:bg-spice-canvas md:hidden"
            >
              <Filter className="h-4 w-4 text-saffron-700" />
              <span>Filters</span>
              {activeFilterCount > 0 && (
                <Badge variant="saffron" size="xs">
                  {activeFilterCount}
                </Badge>
              )}
            </button>

            {/* Sort Dropdown */}
            <div className="flex items-center gap-1.5 text-xs">
              <ArrowUpDown className="h-3.5 w-3.5 text-spice-muted hidden sm:inline" />
              <label htmlFor="catalog-sort" className="text-spice-stone font-medium hidden sm:inline">
                Sort:
              </label>
              <select
                id="catalog-sort"
                value={currentOrdering}
                onChange={(e) => updateFilters({ ordering: e.target.value })}
                className="rounded-lg border border-spice-border bg-white px-3 py-2 text-xs font-semibold text-spice-black focus:border-saffron-600 focus:outline-none focus:ring-2 focus:ring-saffron-500/20 cursor-pointer"
              >
                {SORT_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Active Filter Badges Bar (if any filter active) */}
        {activeFilterCount > 0 && (
          <div className="mb-6 flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-spice-stone">Active Filters:</span>

            {currentCategory && (
              <span className="inline-flex items-center gap-1 rounded-md bg-saffron-50 border border-saffron-200 px-2.5 py-1 text-xs font-medium text-saffron-900">
                Category: {activeCategoryObj?.name || currentCategory}
                <button
                  type="button"
                  onClick={() => updateFilters({ category: '' })}
                  className="hover:text-red-600"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </span>
            )}

            {currentTier && (
              <span className="inline-flex items-center gap-1 rounded-md bg-amber-50 border border-amber-200 px-2.5 py-1 text-xs font-medium text-amber-900">
                Tier: {currentTier === 'RESERVE' ? 'Reserve Heritage' : 'Everyday'}
                <button
                  type="button"
                  onClick={() => updateFilters({ tier: '' })}
                  className="hover:text-red-600"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </span>
            )}

            {currentForm && (
              <span className="inline-flex items-center gap-1 rounded-md bg-stone-100 border border-stone-200 px-2.5 py-1 text-xs font-medium text-stone-800">
                Form: {currentForm}
                <button
                  type="button"
                  onClick={() => updateFilters({ form: '' })}
                  className="hover:text-red-600"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </span>
            )}

            {currentSearch && (
              <span className="inline-flex items-center gap-1 rounded-md bg-spice-canvas border border-spice-border px-2.5 py-1 text-xs font-medium text-spice-black">
                Keyword: &ldquo;{currentSearch}&rdquo;
                <button
                  type="button"
                  onClick={() => {
                    setSearchInput('');
                    updateFilters({ search: '' });
                  }}
                  className="hover:text-red-600"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </span>
            )}

            <button
              type="button"
              onClick={resetAllFilters}
              className="inline-flex items-center gap-1 text-xs font-semibold text-saffron-700 hover:text-saffron-800 ml-2"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Reset All
            </button>
          </div>
        )}

        {/* Main 2-Column Layout */}
        <div className="grid grid-cols-1 gap-8 md:grid-cols-4">
          {/* Desktop Sidebar Filters */}
          <aside className="hidden md:block md:col-span-1 space-y-6">
            {/* Categories Filter */}
            <div className="rounded-xl border border-spice-border bg-white p-4 shadow-2xs">
              <h3 className="text-xs font-bold uppercase tracking-wider text-spice-stone mb-3 flex items-center justify-between">
                <span>Categories</span>
                {currentCategory && (
                  <button
                    type="button"
                    onClick={() => updateFilters({ category: '' })}
                    className="text-[11px] font-semibold text-saffron-700 hover:underline lowercase"
                  >
                    clear
                  </button>
                )}
              </h3>
              <ul className="space-y-1">
                <li>
                  <button
                    type="button"
                    onClick={() => updateFilters({ category: '' })}
                    className={`w-full flex items-center justify-between rounded-lg px-2.5 py-2 text-xs font-medium transition-colors ${
                      !currentCategory
                        ? 'bg-saffron-50 text-saffron-900 font-semibold'
                        : 'text-spice-black hover:bg-spice-canvas'
                    }`}
                  >
                    <span>All Spices</span>
                    {!currentCategory && <Check className="h-3.5 w-3.5 text-saffron-700" />}
                  </button>
                </li>
                {categories.map((cat) => {
                  const isSelected = currentCategory === cat.slug;
                  return (
                    <li key={cat.id || cat.slug}>
                      <button
                        type="button"
                        onClick={() => updateFilters({ category: cat.slug })}
                        className={`w-full flex items-center justify-between rounded-lg px-2.5 py-2 text-xs font-medium transition-colors text-left ${
                          isSelected
                            ? 'bg-saffron-50 text-saffron-900 font-semibold'
                            : 'text-spice-black hover:bg-spice-canvas'
                        }`}
                      >
                        <span className="truncate">{cat.name}</span>
                        {isSelected && <Check className="h-3.5 w-3.5 text-saffron-700 shrink-0" />}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>

            {/* Quality Tier Filter */}
            <div className="rounded-xl border border-spice-border bg-white p-4 shadow-2xs">
              <h3 className="text-xs font-bold uppercase tracking-wider text-spice-stone mb-3">
                Estate Tier
              </h3>
              <div className="flex flex-col gap-1.5">
                {TIER_OPTIONS.map((opt) => {
                  const isSelected = currentTier === opt.value;
                  return (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => updateFilters({ tier: opt.value })}
                      className={`flex items-center justify-between rounded-lg px-2.5 py-2 text-xs font-medium transition-colors text-left ${
                        isSelected
                          ? 'bg-amber-50 text-amber-900 font-semibold border border-amber-200'
                          : 'text-spice-black hover:bg-spice-canvas border border-transparent'
                      }`}
                    >
                      <span className="flex items-center gap-1.5">
                        {opt.value === 'RESERVE' && <Sparkles className="h-3.5 w-3.5 text-amber-600" />}
                        {opt.label}
                      </span>
                      {isSelected && <Check className="h-3.5 w-3.5 text-amber-700" />}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Spice Form Filter */}
            <div className="rounded-xl border border-spice-border bg-white p-4 shadow-2xs">
              <h3 className="text-xs font-bold uppercase tracking-wider text-spice-stone mb-3">
                Spice Form
              </h3>
              <div className="flex flex-col gap-1.5">
                {FORM_OPTIONS.map((opt) => {
                  const isSelected = currentForm === opt.value;
                  return (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => updateFilters({ form: opt.value })}
                      className={`flex items-center justify-between rounded-lg px-2.5 py-2 text-xs font-medium transition-colors text-left ${
                        isSelected
                          ? 'bg-saffron-50 text-saffron-900 font-semibold border border-saffron-200'
                          : 'text-spice-black hover:bg-spice-canvas border border-transparent'
                      }`}
                    >
                      <span>{opt.label}</span>
                      {isSelected && <Check className="h-3.5 w-3.5 text-saffron-700" />}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Heritage Origin Stamp Notice */}
            <div className="rounded-xl border border-dashed border-spice-border bg-spice-canvas/80 p-4 text-center">
              <span className="text-[11px] font-semibold text-saffron-800 uppercase tracking-wider block mb-1">
                Direct From Western Ghats
              </span>
              <p className="text-[11px] text-spice-stone leading-relaxed">
                Zero fillers, zero artificial colorants, packed at source under FSSAI license.
              </p>
            </div>
          </aside>

          {/* Product Grid & States Area */}
          <main className="md:col-span-3">
            {/* Loading State */}
            {isLoading && (
              <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-3 gap-3.5 sm:gap-4 md:gap-5">
                {Array.from({ length: 6 }).map((_, idx) => (
                  <ProductCardSkeleton key={idx} />
                ))}
              </div>
            )}

            {/* Error State */}
            {!isLoading && error && (
              <ErrorState
                title="Failed to load spices"
                message={error}
                onRetry={fetchProducts}
                className="py-16"
              />
            )}

            {/* Empty State */}
            {!isLoading && !error && products.length === 0 && (
              <EmptyState
                title="No spices matched your filters"
                description="Try refining your search keyword, selecting a different estate tier, or clearing your active filters."
                action={
                  <Button variant="primary" size="sm" onClick={resetAllFilters} leftIcon={<RotateCcw className="h-4 w-4" />}>
                    Clear All Filters
                  </Button>
                }
                className="py-16"
              />
            )}

            {/* Product Cards Grid */}
            {!isLoading && !error && products.length > 0 && (
              <>
                <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-3 gap-3.5 sm:gap-4 md:gap-5">
                  {products.map((product) => (
                    <ProductCard key={product.id || product.slug} product={product} />
                  ))}
                </div>

                {/* Pagination Controls */}
                {pagination.total_pages > 1 && (
                  <div className="mt-10 flex items-center justify-between border-t border-spice-borderSubtle pt-6">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={!pagination.previous}
                      onClick={() => updateFilters({ page: currentPage - 1 })}
                    >
                      Previous
                    </Button>

                    <span className="text-xs font-medium text-spice-stone">
                      Page <strong className="text-spice-black">{pagination.page}</strong> of{' '}
                      <strong className="text-spice-black">{pagination.total_pages}</strong>
                    </span>

                    <Button
                      variant="outline"
                      size="sm"
                      disabled={!pagination.next}
                      onClick={() => updateFilters({ page: currentPage + 1 })}
                    >
                      Next
                    </Button>
                  </div>
                )}
              </>
            )}
          </main>
        </div>
      </div>

      {/* Mobile Filters Drawer */}
      <Drawer
        isOpen={isMobileFilterOpen}
        onClose={() => setIsMobileFilterOpen(false)}
        title="Filter Spices"
        description="Refine catalog by category, tier, or spice form"
        placement="left"
        footer={
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="md"
              className="flex-1"
              onClick={() => {
                resetAllFilters();
                setIsMobileFilterOpen(false);
              }}
            >
              Reset
            </Button>
            <Button
              variant="primary"
              size="md"
              className="flex-1"
              onClick={() => setIsMobileFilterOpen(false)}
            >
              Show Results
            </Button>
          </div>
        }
      >
        <div className="space-y-6">
          {/* Categories in drawer */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-spice-stone mb-2">Category</h4>
            <div className="space-y-1">
              <button
                type="button"
                onClick={() => updateFilters({ category: '' })}
                className={`w-full flex items-center justify-between rounded-lg px-3 py-2 text-xs font-medium text-left ${
                  !currentCategory ? 'bg-saffron-50 text-saffron-900 font-semibold' : 'text-spice-black'
                }`}
              >
                <span>All Categories</span>
                {!currentCategory && <Check className="h-4 w-4 text-saffron-700" />}
              </button>
              {categories.map((cat) => {
                const isSelected = currentCategory === cat.slug;
                return (
                  <button
                    key={cat.slug}
                    type="button"
                    onClick={() => updateFilters({ category: cat.slug })}
                    className={`w-full flex items-center justify-between rounded-lg px-3 py-2 text-xs font-medium text-left ${
                      isSelected ? 'bg-saffron-50 text-saffron-900 font-semibold' : 'text-spice-black'
                    }`}
                  >
                    <span>{cat.name}</span>
                    {isSelected && <Check className="h-4 w-4 text-saffron-700" />}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Tier in drawer */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-spice-stone mb-2">Quality Tier</h4>
            <div className="space-y-1">
              {TIER_OPTIONS.map((opt) => {
                const isSelected = currentTier === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => updateFilters({ tier: opt.value })}
                    className={`w-full flex items-center justify-between rounded-lg px-3 py-2 text-xs font-medium text-left ${
                      isSelected ? 'bg-amber-50 text-amber-900 font-semibold' : 'text-spice-black'
                    }`}
                  >
                    <span>{opt.label}</span>
                    {isSelected && <Check className="h-4 w-4 text-amber-700" />}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Form in drawer */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-spice-stone mb-2">Spice Form</h4>
            <div className="space-y-1">
              {FORM_OPTIONS.map((opt) => {
                const isSelected = currentForm === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => updateFilters({ form: opt.value })}
                    className={`w-full flex items-center justify-between rounded-lg px-3 py-2 text-xs font-medium text-left ${
                      isSelected ? 'bg-saffron-50 text-saffron-900 font-semibold' : 'text-spice-black'
                    }`}
                  >
                    <span>{opt.label}</span>
                    {isSelected && <Check className="h-4 w-4 text-saffron-700" />}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </Drawer>
    </div>
  );
}

export default function ProductsPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-spice-canvas py-12">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Array.from({ length: 8 }).map((_, idx) => (
                <ProductCardSkeleton key={idx} />
              ))}
            </div>
          </div>
        </div>
      }
    >
      <ProductsContent />
    </Suspense>
  );
}
