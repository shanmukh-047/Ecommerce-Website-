'use client';

import React, { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useParams, useRouter } from 'next/navigation';
import {
  ChevronRight,
  ShieldCheck,
  MapPin,
  Sparkles,
  Award,
  Calendar,
  Truck,
  CheckCircle2,
  Share2,
  Package,
  FileText,
  Heart,
  ShoppingCart,
  Plus,
  Minus,
  Check,
} from 'lucide-react';
import catalogService from '../../../services/catalogService';
import { useCart } from '../../../context/CartContext';
import { useToast } from '../../../components/common/Toast';
import Button from '../../../components/common/Button';
import Badge from '../../../components/common/Badge';
import Skeleton from '../../../components/common/Skeleton';
import ErrorState from '../../../components/common/ErrorState';

export default function ProductDetailPage() {
  const params = useParams();
  const router = useRouter();
  const slug = params?.slug;

  const { items = [], addToCart, updateQuantity, openCart } = useCart() || {};
  const { success, error: showToastError } = useToast();

  const [product, setProduct] = useState(null);
  const [selectedVariant, setSelectedVariant] = useState(null);
  const [activeImageIndex, setActiveImageIndex] = useState(0);
  const [purchaseQuantity, setPurchaseQuantity] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [isAdding, setIsAdding] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('provenance');

  // Load product by slug
  useEffect(() => {
    if (!slug) return;
    let isMounted = true;

    async function loadProduct() {
      setIsLoading(true);
      setError(null);
      try {
        const data = await catalogService.getProductBySlug(slug);
        if (isMounted && data) {
          setProduct(data);
          // Set default variant: is_most_chosen or first variant
          const vars = data.variants || [];
          const defaultVar = vars.find((v) => v.is_most_chosen) || vars[0] || null;
          setSelectedVariant(defaultVar);
        }
      } catch (err) {
        console.error('Failed to load product detail:', err);
        if (isMounted) {
          setError(err.message || 'The requested spice could not be found.');
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadProduct();
    return () => {
      isMounted = false;
    };
  }, [slug]);

  // Gallery image list (backend images array or hero_image fallback)
  const galleryImages = useMemo(() => {
    if (!product) return [];
    if (product.images && product.images.length > 0) {
      return product.images.map((img) => img.image);
    }
    if (product.hero_image) {
      return [product.hero_image];
    }
    return [];
  }, [product]);

  // Check if selected variant is already in cart
  const cartItem = useMemo(() => {
    if (!selectedVariant?.id || !items) return null;
    return items.find((i) => String(i.variant_id) === String(selectedVariant.id));
  }, [selectedVariant, items]);

  const activeCartQty = cartItem ? cartItem.quantity : 0;

  // Active pricing calculations
  const price = useMemo(() => {
    if (selectedVariant?.selling_price) return parseFloat(selectedVariant.selling_price);
    return 0;
  }, [selectedVariant]);

  const mrp = useMemo(() => {
    if (selectedVariant?.mrp) return parseFloat(selectedVariant.mrp);
    return 0;
  }, [selectedVariant]);

  const discountPercent = useMemo(() => {
    if (selectedVariant?.discount_percentage !== undefined) {
      return Number(selectedVariant.discount_percentage);
    }
    if (mrp > price && mrp > 0) {
      return Math.round(((mrp - price) / mrp) * 100);
    }
    return 0;
  }, [selectedVariant, mrp, price]);

  const savingsAmount = useMemo(() => {
    if (selectedVariant?.savings_amount) return selectedVariant.savings_amount;
    if (mrp > price) return (mrp - price).toFixed(2);
    return '0.00';
  }, [selectedVariant, mrp, price]);

  // Add to cart action
  const handleAddToCart = async (andCheckout = false) => {
    if (!selectedVariant?.id) return;
    setIsAdding(true);
    try {
      if (addToCart) {
        await addToCart(selectedVariant.id, purchaseQuantity, !andCheckout);
      }
      if (andCheckout) {
        router.push('/checkout');
      }
    } catch (err) {
      // Toast is handled in CartContext
    } finally {
      setIsAdding(false);
    }
  };

  // Direct share link
  const handleShare = () => {
    if (navigator.share) {
      navigator
        .share({
          title: product?.name || 'Bharat Masala',
          url: window.location.href,
        })
        .catch(() => {});
    } else {
      navigator.clipboard?.writeText(window.location.href);
      success('Link copied to clipboard', 'Share');
    }
  };

  // Loading skeleton layout
  if (isLoading) {
    return (
      <div className="min-h-screen bg-spice-canvas pb-20 pt-6">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <Skeleton height="16px" width="220px" className="mb-6" />
          <div className="grid grid-cols-1 gap-10 lg:grid-cols-2">
            <div>
              <Skeleton height="420px" className="w-full rounded-2xl mb-4" />
              <div className="flex gap-3">
                <Skeleton height="70px" width="70px" className="rounded-lg" />
                <Skeleton height="70px" width="70px" className="rounded-lg" />
                <Skeleton height="70px" width="70px" className="rounded-lg" />
              </div>
            </div>
            <div className="space-y-4">
              <Skeleton height="14px" width="120px" />
              <Skeleton height="32px" width="80%" />
              <Skeleton height="20px" width="50%" />
              <Skeleton height="40px" width="180px" className="my-4" />
              <Skeleton height="90px" className="w-full rounded-xl" />
              <Skeleton height="48px" className="w-full rounded-xl" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Error layout
  if (error || !product) {
    return (
      <div className="min-h-screen bg-spice-canvas flex items-center justify-center p-4">
        <ErrorState
          title="Spice Not Found"
          message={error || 'This spice product might have been discontinued or moved to another estate batch.'}
          retryLabel="Explore All Spices"
          onRetry={() => router.push('/products')}
          className="max-w-lg w-full py-16"
        />
      </div>
    );
  }

  const categoryName = product.category?.name || 'Spices';
  const categorySlug = product.category?.slug;
  const currentImage = galleryImages[activeImageIndex] || null;
  const variants = product.variants || [];

  return (
    <div className="min-h-screen bg-spice-canvas pb-20 pt-4 sm:pt-6">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Breadcrumb Navigation */}
        <nav aria-label="Breadcrumb" className="mb-6 flex flex-wrap items-center text-xs text-spice-stone">
          <Link href="/" className="hover:text-saffron-700 transition-colors">
            Home
          </Link>
          <ChevronRight className="mx-1.5 h-3.5 w-3.5 text-spice-muted shrink-0" />
          <Link href="/products" className="hover:text-saffron-700 transition-colors">
            Spices & Pantry
          </Link>
          {categorySlug && (
            <>
              <ChevronRight className="mx-1.5 h-3.5 w-3.5 text-spice-muted shrink-0" />
              <Link href={`/products?category=${categorySlug}`} className="hover:text-saffron-700 transition-colors">
                {categoryName}
              </Link>
            </>
          )}
          <ChevronRight className="mx-1.5 h-3.5 w-3.5 text-spice-muted shrink-0" />
          <span className="font-semibold text-spice-black truncate max-w-[200px] sm:max-w-xs">{product.name}</span>
        </nav>

        {/* Product Details Main 2-Column Hero */}
        <div className="grid grid-cols-1 gap-10 lg:grid-cols-12 mb-16">
          {/* Left Column: Image Gallery (5 cols on lg) */}
          <div className="lg:col-span-6 flex flex-col">
            <div className="relative aspect-square w-full overflow-hidden rounded-2xl bg-white border border-spice-border shadow-subtle flex items-center justify-center">
              {/* Badges Overlay */}
              <div className="absolute top-3 left-3 z-10 flex flex-col gap-1.5 items-start">
                {discountPercent > 0 && (
                  <Badge variant="discount" size="sm">
                    {discountPercent}% OFF
                  </Badge>
                )}
                {product.tier === 'RESERVE' && (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-950/90 px-3 py-1 text-xs font-semibold tracking-wider text-amber-200 backdrop-blur-xs shadow-sm">
                    <Sparkles className="h-3.5 w-3.5 text-amber-400" />
                    Reserve Grade
                  </span>
                )}
              </div>

              <div className="absolute top-3 right-3 z-10 flex gap-2">
                {product.is_bestseller && (
                  <Badge variant="saffron" size="sm">
                    Bestseller
                  </Badge>
                )}
                <button
                  type="button"
                  onClick={handleShare}
                  aria-label="Share product"
                  className="h-8 w-8 rounded-full bg-white/80 backdrop-blur-xs flex items-center justify-center text-spice-stone hover:text-spice-black hover:bg-white shadow-2xs transition-colors"
                >
                  <Share2 className="h-4 w-4" />
                </button>
              </div>

              {/* Main Image */}
              {currentImage ? (
                <Image
                  src={currentImage}
                  alt={product.name || 'Authentic Spice'}
                  fill
                  priority
                  sizes="(max-width: 1024px) 100vw, 50vw"
                  className="object-cover object-center transition-all duration-300"
                />
              ) : (
                /* Fallback Graphic */
                <div className="flex flex-col items-center justify-center text-spice-muted h-full w-full p-8 text-center">
                  <div className="h-20 w-20 rounded-full bg-saffron-100/60 flex items-center justify-center mb-3 text-saffron-700">
                    <ShieldCheck className="h-10 w-10" />
                  </div>
                  <h3 className="text-sm font-bold text-spice-black uppercase tracking-wider mb-1">
                    100% Authentic Estate Spice
                  </h3>
                  <span className="text-xs text-spice-stone">Western Ghats Sourced & Pure</span>
                </div>
              )}
            </div>

            {/* Thumbnail Strip (if multi-image) */}
            {galleryImages.length > 1 && (
              <div className="mt-4 flex gap-3 overflow-x-auto pb-1">
                {galleryImages.map((imgUrl, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => setActiveImageIndex(idx)}
                    className={`relative h-18 w-18 shrink-0 overflow-hidden rounded-xl border-2 transition-all ${
                      activeImageIndex === idx
                        ? 'border-saffron-600 shadow-2xs ring-2 ring-saffron-500/20'
                        : 'border-spice-border opacity-70 hover:opacity-100'
                    }`}
                  >
                    <Image
                      src={imgUrl}
                      alt={`${product.name} thumbnail ${idx + 1}`}
                      fill
                      sizes="72px"
                      className="object-cover object-center"
                    />
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Right Column: Information, Variant Selector, Add to Cart (7 cols on lg) */}
          <div className="lg:col-span-6 flex flex-col justify-between">
            <div>
              {/* Category & Origin Region */}
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-saffron-800">
                  {categoryName}
                </span>
                {product.origin_region && (
                  <>
                    <span className="text-spice-muted">•</span>
                    <span className="inline-flex items-center gap-1 text-xs text-spice-stone font-medium">
                      <MapPin className="h-3.5 w-3.5 text-saffron-600" />
                      {product.origin_region}
                    </span>
                  </>
                )}
              </div>

              {/* Title & Grade */}
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-spice-black font-display mb-2">
                {product.name}
              </h1>

              {product.grade && (
                <div className="inline-flex items-center gap-1.5 rounded-md bg-stone-100 px-2.5 py-1 text-xs font-semibold text-stone-800 mb-4">
                  <Award className="h-3.5 w-3.5 text-saffron-700" />
                  <span>Grade: {product.grade}</span>
                </div>
              )}

              {/* Short Description */}
              {product.short_description && (
                <p className="text-sm text-spice-stone leading-relaxed mb-6">
                  {product.short_description}
                </p>
              )}

              {/* Dynamic Price Display */}
              <div className="mb-6 rounded-xl border border-spice-border bg-white p-4 shadow-2xs">
                <div className="flex items-baseline gap-3">
                  <span className="text-3xl font-extrabold text-spice-black tabular-nums">
                    ₹{Math.round(price)}
                  </span>
                  {mrp > price && (
                    <span className="text-base text-spice-muted line-through tabular-nums">
                      ₹{Math.round(mrp)}
                    </span>
                  )}
                  {discountPercent > 0 && (
                    <Badge variant="discount" size="sm">
                      {discountPercent}% OFF
                    </Badge>
                  )}
                </div>

                {mrp > price && (
                  <p className="mt-1 text-xs font-semibold text-emerald-700">
                    You save ₹{savingsAmount} on this pack
                  </p>
                )}

                <div className="mt-2 text-[11px] text-spice-muted">
                  <span>Inclusive of all applicable taxes (GST {product.legal_metrology?.gst_rate || 5}%)</span>
                </div>
              </div>

              {/* Pack-Size Variant Selection */}
              {variants.length > 0 && (
                <div className="mb-6">
                  <div className="flex items-center justify-between mb-2.5">
                    <label className="text-xs font-bold uppercase tracking-wider text-spice-black">
                      Select Pack Size
                    </label>
                    {selectedVariant?.sku && (
                      <span className="text-[11px] text-spice-stone">
                        SKU: <code className="font-mono">{selectedVariant.sku}</code>
                      </span>
                    )}
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                    {variants.map((v) => {
                      const isSelected = selectedVariant?.id === v.id;
                      const vPrice = parseFloat(v.selling_price || 0);
                      const vMrp = parseFloat(v.mrp || 0);

                      return (
                        <button
                          key={v.id}
                          type="button"
                          onClick={() => setSelectedVariant(v)}
                          className={`relative flex flex-col p-3 rounded-xl border text-left transition-all ${
                            isSelected
                              ? 'border-saffron-600 bg-saffron-50/40 ring-2 ring-saffron-500/20 shadow-2xs'
                              : 'border-spice-border bg-white hover:border-spice-stone/40'
                          }`}
                        >
                          {v.is_most_chosen && (
                            <span className="absolute -top-2 right-2 rounded-full bg-saffron-600 px-2 py-0.2 text-[9px] font-bold uppercase tracking-wider text-white">
                              Popular
                            </span>
                          )}

                          <span className="text-xs font-bold text-spice-black mb-1">
                            {v.variant_name || `${v.weight_in_grams}g`}
                          </span>

                          <div className="flex items-baseline gap-1.5 mt-auto">
                            <span className="text-sm font-extrabold text-spice-black tabular-nums">
                              ₹{Math.round(vPrice)}
                            </span>
                            {vMrp > vPrice && (
                              <span className="text-[11px] text-spice-muted line-through tabular-nums">
                                ₹{Math.round(vMrp)}
                              </span>
                            )}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Quantity Selector & Action Buttons */}
              <div className="mb-6 flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                {/* Quantity Input */}
                <div className="flex items-center justify-between rounded-xl border border-spice-border bg-white px-3 py-2 shrink-0">
                  <span className="text-xs font-semibold text-spice-stone mr-3">Qty</span>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      aria-label="Decrease quantity"
                      onClick={() => setPurchaseQuantity((q) => Math.max(1, q - 1))}
                      disabled={purchaseQuantity <= 1}
                      className="h-7 w-7 rounded-lg border border-spice-border flex items-center justify-center text-spice-black hover:bg-spice-canvas disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      <Minus className="h-3.5 w-3.5" />
                    </button>
                    <span className="w-8 text-center text-sm font-bold tabular-nums text-spice-black">
                      {purchaseQuantity}
                    </span>
                    <button
                      type="button"
                      aria-label="Increase quantity"
                      onClick={() => setPurchaseQuantity((q) => Math.min(10, q + 1))}
                      disabled={purchaseQuantity >= 10}
                      className="h-7 w-7 rounded-lg border border-spice-border flex items-center justify-center text-spice-black hover:bg-spice-canvas disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      <Plus className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>

                {/* Primary Add to Cart Button */}
                <Button
                  variant="primary"
                  size="lg"
                  onClick={() => handleAddToCart(false)}
                  isLoading={isAdding}
                  leftIcon={<ShoppingCart className="h-5 w-5" />}
                  className="flex-1 shadow-md font-semibold text-sm uppercase tracking-wider"
                >
                  {activeCartQty > 0 ? `Add More (${activeCartQty} in cart)` : 'Add to Basket'}
                </Button>

                {/* Buy Now / Quick Checkout Button */}
                <Button
                  variant="secondary"
                  size="lg"
                  onClick={() => handleAddToCart(true)}
                  disabled={isAdding}
                  className="font-semibold text-sm"
                >
                  Buy Now
                </Button>
              </div>

              {/* Trust Badges */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 border-t border-spice-borderSubtle pt-4">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
                  <span className="text-[11px] font-medium text-spice-stone">100% Single Origin</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
                  <span className="text-[11px] font-medium text-spice-stone">No Preservatives</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
                  <span className="text-[11px] font-medium text-spice-stone">FSSAI Certified</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
                  <span className="text-[11px] font-medium text-spice-stone">Fresh Batch Milled</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Heritage, Metrology, and Culinary Story Tabs */}
        <div className="rounded-2xl border border-spice-border bg-white p-6 sm:p-8 shadow-subtle mb-16">
          <div className="border-b border-spice-borderSubtle mb-6 flex space-x-6 overflow-x-auto">
            <button
              type="button"
              onClick={() => setActiveTab('provenance')}
              className={`pb-3 text-sm font-bold transition-all border-b-2 whitespace-nowrap ${
                activeTab === 'provenance'
                  ? 'border-saffron-600 text-saffron-800'
                  : 'border-transparent text-spice-stone hover:text-spice-black'
              }`}
            >
              Estate Provenance & Terroir
            </button>

            {product.sharada_note && (
              <button
                type="button"
                onClick={() => setActiveTab('sharada')}
                className={`pb-3 text-sm font-bold transition-all border-b-2 whitespace-nowrap flex items-center gap-1.5 ${
                  activeTab === 'sharada'
                    ? 'border-saffron-600 text-saffron-800'
                    : 'border-transparent text-spice-stone hover:text-spice-black'
                }`}
              >
                <Sparkles className="h-4 w-4 text-saffron-600" />
                <span>Sharada&apos;s Kitchen Note</span>
              </button>
            )}

            <button
              type="button"
              onClick={() => setActiveTab('metrology')}
              className={`pb-3 text-sm font-bold transition-all border-b-2 whitespace-nowrap flex items-center gap-1.5 ${
                activeTab === 'metrology'
                  ? 'border-saffron-600 text-saffron-800'
                  : 'border-transparent text-spice-stone hover:text-spice-black'
              }`}
            >
              <FileText className="h-4 w-4 text-spice-stone" />
              <span>Legal Metrology & Packaging</span>
            </button>
          </div>

          {/* Tab Content: Provenance */}
          {activeTab === 'provenance' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-base font-bold text-spice-black font-display mb-2">
                  The Story of this Harvest
                </h3>
                <p className="text-sm text-spice-stone leading-relaxed">
                  {product.plantation_provenance || product.detailed_description || product.short_description}
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4 border-t border-spice-borderSubtle">
                <div className="rounded-xl bg-spice-canvas/80 p-3.5 border border-spice-border">
                  <span className="text-[11px] font-semibold text-spice-stone uppercase tracking-wider block mb-1">
                    Region of Origin
                  </span>
                  <span className="text-sm font-bold text-spice-black">
                    {product.origin_region || 'Western Ghats, India'}
                  </span>
                </div>

                {product.harvest_date && (
                  <div className="rounded-xl bg-spice-canvas/80 p-3.5 border border-spice-border">
                    <span className="text-[11px] font-semibold text-spice-stone uppercase tracking-wider block mb-1">
                      Harvest Season
                    </span>
                    <span className="text-sm font-bold text-spice-black">
                      {product.harvest_date}
                    </span>
                  </div>
                )}

                {product.grinding_date && (
                  <div className="rounded-xl bg-spice-canvas/80 p-3.5 border border-spice-border">
                    <span className="text-[11px] font-semibold text-spice-stone uppercase tracking-wider block mb-1">
                      Milling & Grinding Date
                    </span>
                    <span className="text-sm font-bold text-spice-black">
                      {product.grinding_date}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Tab Content: Sharada's Kitchen Note */}
          {activeTab === 'sharada' && product.sharada_note && (
            <div className="rounded-xl bg-amber-50/60 border border-amber-200 p-5">
              <div className="flex items-center gap-2 mb-3">
                <div className="h-8 w-8 rounded-full bg-saffron-600 text-white flex items-center justify-center font-bold text-xs">
                  BM
                </div>
                <div>
                  <h4 className="text-sm font-bold text-amber-950">Grandmother Sharada&apos;s Guidance</h4>
                  <span className="text-xs text-amber-800">Master Blender & Culinary Matriarch</span>
                </div>
              </div>
              <p className="text-sm text-amber-900 leading-relaxed italic font-serif">
                &ldquo;{product.sharada_note}&rdquo;
              </p>
            </div>
          )}

          {/* Tab Content: Legal Metrology (FSSAI compliance) */}
          {activeTab === 'metrology' && (
            <div className="space-y-4">
              <h3 className="text-sm font-bold uppercase tracking-wider text-spice-black mb-3">
                Mandatory Declarations (Legal Metrology Act, 2009)
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="rounded-xl border border-spice-border p-4 bg-spice-canvas/40">
                  <span className="text-xs font-semibold text-spice-stone block mb-1">
                    FSSAI Central License
                  </span>
                  <span className="text-sm font-mono font-bold text-spice-black">
                    {product.legal_metrology?.fssai_license || '11223344556677'}
                  </span>
                </div>

                <div className="rounded-xl border border-spice-border p-4 bg-spice-canvas/40">
                  <span className="text-xs font-semibold text-spice-stone block mb-1">
                    HSN Tariff Classification
                  </span>
                  <span className="text-sm font-mono font-bold text-spice-black">
                    {product.legal_metrology?.hsn_code || '09096139'}
                  </span>
                </div>

                <div className="rounded-xl border border-spice-border p-4 bg-spice-canvas/40 md:col-span-2">
                  <span className="text-xs font-semibold text-spice-stone block mb-1">
                    Packaged & Marketed By
                  </span>
                  <p className="text-xs text-spice-black leading-relaxed">
                    <strong>{product.legal_metrology?.packer_name || 'Bharat Masala Products Pvt Ltd'}</strong>
                    <br />
                    {product.legal_metrology?.packer_address ||
                      'B.H. Road, Industrial Area, Shimoga, Karnataka, India - 577201'}
                  </p>
                </div>

                <div className="rounded-xl border border-spice-border p-4 bg-spice-canvas/40 md:col-span-2">
                  <span className="text-xs font-semibold text-spice-stone block mb-1">
                    Best Before Guidance & Storage
                  </span>
                  <p className="text-xs text-spice-black leading-relaxed">
                    {product.legal_metrology?.best_before_guidance ||
                      '12 months from packing date when kept in cool, dry conditions away from moisture.'}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Back to All Spices Button */}
        <div className="text-center">
          <Link
            href="/products"
            className="inline-flex items-center gap-2 text-xs font-bold text-saffron-800 hover:text-saffron-900 uppercase tracking-wider hover:underline"
          >
            ← Back to All Spices & Collections
          </Link>
        </div>
      </div>
    </div>
  );
}
