'use client';

import React, { useState, useMemo } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { Plus, ShieldCheck, Sparkles, MapPin, Award } from 'lucide-react';
import Badge from './Badge';
import QuantitySelector from './QuantitySelector';
import Button from './Button';
import { useCart } from '../../context/CartContext';

/**
 * Production-ready ProductCard component for Bharat Masala.
 * Strictly consumes backend ProductListSerializer output:
 * - id, name, slug, category, tier, form, origin_region, grade, is_bestseller
 * - hero_image, starting_price, starting_price_label, variants
 * Seamlessly integrates with CartContext for live cart quantity and dynamic pack switching.
 */
export default function ProductCard({
  product,
  cartQuantity: propCartQuantity,
  onAddToCart,
  onQuantityChange,
  onProductClick,
  className = '',
}) {
  const router = useRouter();
  const { items = [], addToCart, updateQuantity } = useCart() || {};

  const {
    id,
    slug,
    name = 'Authentic Indian Spice',
    category,
    tier,
    form,
    origin_region,
    origin_stamp,
    grade,
    is_bestseller,
    hero_image,
    starting_price,
    starting_price_label,
    variants = [],
  } = product || {};

  // Extract category display name
  const categoryName = useMemo(() => {
    if (!category) return 'Spices';
    if (typeof category === 'object') return category.name || 'Spices';
    return String(category);
  }, [category]);

  // Selected variant state (defaults to is_most_chosen or first variant)
  const [selectedVariant, setSelectedVariant] = useState(() => {
    if (variants && variants.length > 0) {
      return variants.find((v) => v.is_most_chosen) || variants[0];
    }
    return null;
  });

  // Keep selected variant up to date if product changes
  React.useEffect(() => {
    if (variants && variants.length > 0) {
      setSelectedVariant((prev) => {
        if (prev && variants.some((v) => v.id === prev.id)) {
          return variants.find((v) => v.id === prev.id);
        }
        return variants.find((v) => v.is_most_chosen) || variants[0];
      });
    }
  }, [variants]);

  // Find line item in cart corresponding to currently selected variant
  const cartItem = useMemo(() => {
    if (!selectedVariant?.id || !items) return null;
    return items.find((item) => String(item.variant_id) === String(selectedVariant.id));
  }, [selectedVariant, items]);

  const activeCartQty = propCartQuantity !== undefined ? propCartQuantity : (cartItem ? cartItem.quantity : 0);

  // Pricing calculations
  const price = useMemo(() => {
    if (selectedVariant?.selling_price) return parseFloat(selectedVariant.selling_price);
    if (selectedVariant?.price) return parseFloat(selectedVariant.price);
    if (starting_price) return parseFloat(starting_price);
    return 0;
  }, [selectedVariant, starting_price]);

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

  const hasDiscount = discountPercent > 0;
  const isInStock = selectedVariant ? selectedVariant.is_in_stock !== false : true;
  const displayImage = hero_image || product?.image || null;
  const productUrl = `/products/${slug || id}`;
  const [imgError, setImgError] = useState(false);
  const [imgLoaded, setImgLoaded] = useState(false);

  const handleCardClick = (e) => {
    // If click was on button, pack pill, or interactive element, ignore
    if (e.target.closest('button') || e.target.closest('a') || e.target.closest('input')) {
      return;
    }
    if (onProductClick) {
      onProductClick(slug || id);
    } else {
      router.push(productUrl);
    }
  };

  const handleAddClick = async (e) => {
    e.stopPropagation();
    if (!selectedVariant?.id || !isInStock) return;

    if (onAddToCart) {
      onAddToCart(selectedVariant.id, 1);
    } else if (addToCart) {
      try {
        await addToCart(selectedVariant.id, 1, false);
      } catch (err) {
        console.error('Add to cart failed:', err);
      }
    }
  };

  const handleIncrement = async (e) => {
    e?.stopPropagation?.();
    if (!isInStock) return;

    if (onQuantityChange) {
      onQuantityChange(selectedVariant.id, activeCartQty + 1);
    } else if (cartItem && updateQuantity) {
      await updateQuantity(cartItem.id, activeCartQty + 1);
    } else if (addToCart && selectedVariant?.id) {
      await addToCart(selectedVariant.id, 1, false);
    }
  };

  const handleDecrement = async (e) => {
    e?.stopPropagation?.();
    const newQty = Math.max(0, activeCartQty - 1);
    if (onQuantityChange) {
      onQuantityChange(selectedVariant.id, newQty);
    } else if (cartItem && updateQuantity) {
      await updateQuantity(cartItem.id, newQty);
    }
  };

  return (
    <div
      onClick={handleCardClick}
      className={`group relative flex flex-col justify-between rounded-xl bg-white border border-spice-border p-2.5 sm:p-4 min-w-0 transition-all duration-200 hover:-translate-y-1 hover:shadow-card-hover hover:border-saffron-500/40 cursor-pointer ${className}`}
    >
      <div>
        {/* Top Media Container */}
        <div className="relative aspect-square w-full overflow-hidden rounded-lg bg-spice-canvas mb-3 flex items-center justify-center">
          {/* Discount Badge */}
          {hasDiscount && (
            <div className="absolute top-2 left-2 z-10">
              <Badge variant="discount" size="xs">
                {discountPercent}% OFF
              </Badge>
            </div>
          )}

          {/* Badges container */}
          <div className="absolute top-2 right-2 z-10 flex flex-col gap-1 items-end">
            {is_bestseller && (
              <Badge variant="saffron" size="xs">
                Bestseller
              </Badge>
            )}
            {tier === 'RESERVE' && (
              <span className="inline-flex items-center gap-1 rounded-full bg-amber-950/80 px-2 py-0.5 text-[10px] font-medium tracking-wider text-amber-200 backdrop-blur-xs shadow-2xs">
                <Sparkles className="h-2.5 w-2.5 text-amber-400" />
                Reserve
              </span>
            )}
          </div>

          {/* Optimized Product Image with skeleton */}
          {displayImage && !imgError ? (
            <>
              {!imgLoaded && (
                <div className="absolute inset-0 bg-stone-100 animate-pulse" />
              )}
              <Image
                src={displayImage}
                alt={name}
                fill
                sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw"
                className={`object-cover object-center transition-all duration-300 group-hover:scale-105 ${
                  imgLoaded ? 'opacity-100' : 'opacity-0'
                }`}
                onLoad={() => setImgLoaded(true)}
                onError={() => setImgError(true)}
              />
            </>
          ) : (
            <div className="flex flex-col items-center justify-center text-spice-muted h-full w-full p-4 text-center">
              <div className="h-12 w-12 rounded-full bg-saffron-100/70 flex items-center justify-center mb-1 text-saffron-700">
                <ShieldCheck className="h-6 w-6" />
              </div>
              <span className="text-[11px] font-semibold text-spice-stone uppercase tracking-wider">
                {categoryName}
              </span>
              <span className="text-[10px] text-spice-muted mt-0.5 font-medium">100% Pure Origin</span>
            </div>
          )}

          {/* Out of Stock Overlay */}
          {!isInStock && (
            <div className="absolute inset-0 bg-spice-earth/60 backdrop-blur-xs flex items-center justify-center">
              <span className="rounded-md bg-white/95 px-3 py-1 text-xs font-bold uppercase tracking-wider text-feedback-error shadow-sm">
                Out of Stock
              </span>
            </div>
          )}
        </div>

        {/* Category & Origin Metadata */}
        <div className="flex items-center justify-between gap-1 text-[11px] font-medium text-spice-muted mb-1">
          <span className="truncate uppercase tracking-wider font-semibold text-saffron-800">
            {categoryName}
          </span>
          {origin_region && (
            <span className="inline-flex items-center gap-0.5 text-spice-stone truncate max-w-[130px]" title={origin_region}>
              <MapPin className="h-3 w-3 text-saffron-600 shrink-0" />
              <span className="truncate">{origin_region.split(',')[0]}</span>
            </span>
          )}
        </div>

        {/* Product Name */}
        <h3 className="text-sm font-semibold text-spice-black leading-snug line-clamp-2 min-h-[40px] mb-1 group-hover:text-saffron-700 transition-colors">
          <Link href={productUrl} onClick={(e) => e.stopPropagation()} className="hover:underline focus:outline-none">
            {name}
          </Link>
        </h3>

        {/* Grade or Quality Stamp */}
        {grade && (
          <p className="text-[11px] text-spice-stone mb-2 line-clamp-1 flex items-center gap-1 font-medium">
            <Award className="h-3 w-3 text-saffron-700 shrink-0" />
            <span className="truncate">{grade}</span>
          </p>
        )}

        {/* Pack Size Pills / Variants */}
        {variants.length > 1 && (
          <div className="flex flex-wrap gap-1.5 mb-3" onClick={(e) => e.stopPropagation()}>
            {variants.map((v) => {
              const isSelected = selectedVariant?.id === v.id;
              const weightLabel = v.variant_name || `${v.weight_in_grams}g`;
              return (
                <button
                  key={v.id}
                  type="button"
                  onClick={() => setSelectedVariant(v)}
                  className={`text-[11px] px-2 py-0.5 rounded-md font-medium transition-all ${
                    isSelected
                      ? 'bg-saffron-600 text-white shadow-2xs font-semibold'
                      : 'bg-spice-borderSubtle text-spice-stone hover:bg-spice-border'
                  }`}
                >
                  {weightLabel}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Pricing & Add to Cart Footer */}
      <div className="pt-2 border-t border-spice-borderSubtle flex items-center justify-between gap-1 sm:gap-2 mt-auto min-w-0">
        <div className="flex flex-col min-w-0">
          <div className="flex items-baseline gap-1 flex-wrap">
            <span className="text-sm sm:text-base font-bold text-spice-black tabular-nums">
              ₹{Math.round(price)}
            </span>
            {hasDiscount && mrp > price && (
              <span className="text-[10px] sm:text-xs text-spice-muted line-through tabular-nums">
                ₹{Math.round(mrp)}
              </span>
            )}
          </div>
          {selectedVariant?.variant_name && variants.length <= 1 && (
            <span className="text-[10px] text-spice-muted font-medium truncate">
              {selectedVariant.variant_name}
            </span>
          )}
          {!selectedVariant && starting_price_label && (
            <span className="text-[10px] text-spice-muted font-medium truncate">
              {starting_price_label}
            </span>
          )}
        </div>

        {/* Action Button: ADD or Quantity Stepper */}
        <div className="shrink-0" onClick={(e) => e.stopPropagation()}>
          {!isInStock ? (
            <span className="text-[10px] sm:text-xs font-semibold text-spice-muted py-1 px-1.5">
              Unavailable
            </span>
          ) : activeCartQty > 0 ? (
            <QuantitySelector
              quantity={activeCartQty}
              onIncrement={handleIncrement}
              onDecrement={handleDecrement}
              size="sm"
              variant="solid-saffron"
            />
          ) : (
            <Button
              variant="outline"
              size="sm"
              onClick={handleAddClick}
              leftIcon={<Plus className="h-3 w-3 sm:h-3.5 sm:w-3.5" />}
              className="border-saffron-600 font-semibold px-2 sm:px-3 uppercase tracking-wider text-[11px] sm:text-xs hover:bg-saffron-50"
            >
              ADD
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
