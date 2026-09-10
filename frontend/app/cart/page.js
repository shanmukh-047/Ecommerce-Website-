'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import {
  ShoppingBag,
  ArrowRight,
  Trash2,
  Tag,
  X,
  Check,
  Truck,
  ShieldCheck,
  ChevronRight,
  AlertTriangle,
  RotateCcw,
  Sparkles,
} from 'lucide-react';
import { useCart } from '../../context/CartContext';
import Button from '../../components/common/Button';
import QuantitySelector from '../../components/common/QuantitySelector';
import EmptyState from '../../components/common/EmptyState';
import Modal from '../../components/common/Modal';
import Badge from '../../components/common/Badge';
import Skeleton from '../../components/common/Skeleton';

const FREE_SHIPPING_THRESHOLD = 499;
const STANDARD_SHIPPING_FEE = 50;

export default function CartPage() {
  const router = useRouter();
  const {
    items,
    itemCount,
    subtotal,
    discountAmount,
    netSubtotal,
    appliedCouponCode,
    validationIssuesMap,
    hasValidationIssues,
    isLoading,
    isUpdating,
    isItemUpdating,
    updateQuantity,
    removeItem,
    clearCart,
    applyCoupon,
    removeCoupon,
  } = useCart();

  const [couponInput, setCouponInput] = useState('');
  const [isApplyingCoupon, setIsApplyingCoupon] = useState(false);
  const [isClearModalOpen, setIsClearModalOpen] = useState(false);

  // Shipping math
  const isFreeShipping = subtotal >= FREE_SHIPPING_THRESHOLD;
  const amountNeededForFreeShipping = Math.max(0, FREE_SHIPPING_THRESHOLD - subtotal);
  const freeShippingProgress = Math.min(100, Math.round((subtotal / FREE_SHIPPING_THRESHOLD) * 100));
  const shippingFee = isFreeShipping || items.length === 0 ? 0 : STANDARD_SHIPPING_FEE;
  const finalTotal = netSubtotal + shippingFee;

  const handleApplyCoupon = async (e) => {
    e?.preventDefault();
    if (!couponInput.trim()) return;
    setIsApplyingCoupon(true);
    try {
      await applyCoupon(couponInput.trim().toUpperCase());
      setCouponInput('');
    } catch {
      // Handled by CartContext toast
    } finally {
      setIsApplyingCoupon(false);
    }
  };

  const handleConfirmClear = async () => {
    await clearCart();
    setIsClearModalOpen(false);
  };

  // Loading State
  if (isLoading) {
    return (
      <div className="min-h-screen bg-spice-canvas py-8 sm:py-12">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <Skeleton height="20px" width="180px" className="mb-6" />
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            <div className="lg:col-span-8 space-y-4">
              <Skeleton height="70px" className="w-full rounded-2xl" />
              <Skeleton height="100px" className="w-full rounded-2xl" />
              <Skeleton height="100px" className="w-full rounded-2xl" />
              <Skeleton height="100px" className="w-full rounded-2xl" />
            </div>
            <div className="lg:col-span-4">
              <Skeleton height="360px" className="w-full rounded-2xl" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Empty Cart State
  if (items.length === 0) {
    return (
      <div className="min-h-screen bg-spice-canvas flex items-center justify-center py-16 px-4">
        <div className="max-w-md w-full">
          <EmptyState
            icon={<ShoppingBag className="h-10 w-10 stroke-[1.5] text-saffron-700" />}
            title="Your shopping basket is empty"
            description="Explore our collection of authentic Western Ghats single-origin spices, hand-ground masalas, and estate harvests."
            action={
              <Link href="/products">
                <Button variant="primary" size="md" rightIcon={<ArrowRight className="h-4 w-4" />}>
                  Explore Spices &amp; Pantry
                </Button>
              </Link>
            }
            className="py-14 bg-white shadow-subtle border-spice-border"
          />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-spice-canvas pb-28 pt-4 sm:pt-6">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Breadcrumb */}
        <nav aria-label="Breadcrumb" className="mb-4 flex items-center text-xs text-spice-stone">
          <Link href="/" className="hover:text-saffron-700 transition-colors">
            Home
          </Link>
          <ChevronRight className="mx-1.5 h-3.5 w-3.5 text-spice-muted" />
          <Link href="/products" className="hover:text-saffron-700 transition-colors">
            Spices
          </Link>
          <ChevronRight className="mx-1.5 h-3.5 w-3.5 text-spice-muted" />
          <span className="font-semibold text-spice-black">Shopping Basket</span>
        </nav>

        {/* Page Header */}
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between border-b border-spice-borderSubtle pb-4 gap-2">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl sm:text-3xl font-bold font-display text-spice-black tracking-tight">
              Shopping Basket
            </h1>
            <Badge variant="saffron" size="sm">
              {itemCount} {itemCount === 1 ? 'Item' : 'Items'}
            </Badge>
          </div>

          <button
            type="button"
            onClick={() => setIsClearModalOpen(true)}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-spice-stone hover:text-red-600 transition-colors self-start sm:self-auto"
          >
            <Trash2 className="h-3.5 w-3.5" />
            <span>Clear Basket</span>
          </button>
        </div>

        {/* Validation Issues Alert Banner (if backend reported any stock/variant issue) */}
        {hasValidationIssues && (
          <div className="mb-6 rounded-2xl border border-amber-300 bg-amber-50 p-4 text-amber-900 shadow-2xs">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-amber-950">
                  Cart Inventory Notice
                </h4>
                <p className="mt-0.5 text-xs text-amber-800 leading-relaxed">
                  One or more items in your basket currently exceed available inventory or have been updated by the estate.
                  Please adjust the quantity or remove the affected items before proceeding to checkout.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Main 2-Column Grid */}
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-12 items-start">
          {/* Left Column: Cart Items List (8 cols) */}
          <div className="lg:col-span-8 space-y-4">
            {/* Free Delivery Milestone Progress */}
            <div className="rounded-2xl border border-spice-border bg-white p-4 shadow-subtle">
              <div className="flex items-center justify-between text-xs font-semibold text-spice-black mb-2">
                <span className="flex items-center gap-2">
                  <Truck className="h-4 w-4 text-saffron-600" />
                  {isFreeShipping ? (
                    <strong className="text-emerald-700">Congratulations! You unlocked FREE Delivery.</strong>
                  ) : (
                    <span>
                      Add <strong className="text-saffron-700">₹{amountNeededForFreeShipping.toFixed(0)}</strong> more to unlock FREE Delivery
                    </span>
                  )}
                </span>
                <span className="text-[11px] text-spice-muted font-normal">
                  Threshold: ₹{FREE_SHIPPING_THRESHOLD}
                </span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-spice-canvas">
                <div
                  className="h-full bg-saffron-600 transition-all duration-300 rounded-full"
                  style={{ width: `${freeShippingProgress}%` }}
                />
              </div>
            </div>

            {/* Cart Items Cards */}
            <div className="rounded-2xl border border-spice-border bg-white shadow-subtle overflow-hidden divide-y divide-spice-borderSubtle">
              {items.map((item) => {
                const unitPrice = parseFloat(item.unit_price || 0);
                const lineTotal = parseFloat(item.line_total || 0);
                const itemMrp = parseFloat(item.mrp || 0);
                const isUpdatingThis = isItemUpdating(item.id);
                const issueCode = validationIssuesMap[item.id];

                return (
                  <div
                    key={item.id}
                    className={`p-4 sm:p-5 transition-opacity ${
                      isUpdatingThis ? 'opacity-60' : 'opacity-100'
                    } ${issueCode ? 'bg-amber-50/40' : ''}`}
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center gap-4">
                      {/* Product Thumbnail */}
                      <div className="relative h-20 w-20 sm:h-24 sm:w-24 rounded-xl bg-spice-canvas border border-spice-border overflow-hidden shrink-0 flex items-center justify-center text-spice-muted">
                        {item.product_image ? (
                          <Image
                            src={item.product_image}
                            alt={item.product_name || 'Spice'}
                            fill
                            sizes="96px"
                            className="object-cover object-center"
                          />
                        ) : (
                          <ShoppingBag className="h-8 w-8 stroke-[1.2]" />
                        )}
                      </div>

                      {/* Item Details */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <h3 className="text-sm sm:text-base font-bold text-spice-black leading-snug">
                              {item.product_name}
                            </h3>
                            <p className="text-xs text-spice-stone mt-0.5 font-medium">
                              Pack: {item.variant_name || `${item.weight_in_grams}g`}
                              {item.sku && (
                                <span className="text-spice-muted ml-2 font-mono text-[11px]">
                                  SKU: {item.sku}
                                </span>
                              )}
                            </p>
                          </div>

                          {/* Desktop Delete button */}
                          <button
                            type="button"
                            onClick={() => removeItem(item.id)}
                            disabled={isUpdating}
                            aria-label={`Remove ${item.product_name} from basket`}
                            className="hidden sm:inline-flex p-1.5 text-spice-stone hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>

                        {/* Inventory Issue Pill */}
                        {issueCode && (
                          <div className="mt-2 inline-flex items-center gap-1.5 rounded-md bg-red-50 border border-red-200 px-2 py-0.5 text-[11px] font-semibold text-red-700">
                            <AlertTriangle className="h-3 w-3" />
                            <span>
                              {issueCode === 'INSUFFICIENT_STOCK'
                                ? 'Limited inventory. Please reduce quantity.'
                                : 'Variant unavailable.'}
                            </span>
                          </div>
                        )}

                        {/* Controls & Price Row */}
                        <div className="mt-4 flex items-center justify-between gap-4 pt-2 border-t border-spice-borderSubtle/60 sm:border-0 sm:pt-0">
                          {/* Unit Price Display */}
                          <div className="flex items-baseline gap-1.5">
                            <span className="text-sm font-bold text-spice-black tabular-nums">
                              ₹{Math.round(unitPrice)}
                            </span>
                            {itemMrp > unitPrice && (
                              <span className="text-xs text-spice-muted line-through tabular-nums">
                                ₹{Math.round(itemMrp)}
                              </span>
                            )}
                            <span className="text-[11px] text-spice-muted">/ unit</span>
                          </div>

                          {/* Stepper Selector */}
                          <div className="flex items-center gap-3">
                            <QuantitySelector
                              quantity={item.quantity}
                              min={0}
                              size="sm"
                              onIncrement={() => updateQuantity(item.id, item.quantity + 1)}
                              onDecrement={() => updateQuantity(item.id, item.quantity - 1)}
                              disabled={isUpdating}
                            />

                            {/* Line Total */}
                            <span className="text-base font-extrabold text-spice-black tabular-nums min-w-[70px] text-right">
                              ₹{Math.round(lineTotal)}
                            </span>

                            {/* Mobile Delete Icon */}
                            <button
                              type="button"
                              onClick={() => removeItem(item.id)}
                              disabled={isUpdating}
                              aria-label={`Remove ${item.product_name}`}
                              className="sm:hidden p-1.5 text-spice-stone hover:text-red-600"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Return to Catalog Action */}
            <div className="flex items-center justify-between pt-2">
              <Link
                href="/products"
                className="inline-flex items-center gap-1.5 text-xs font-bold text-saffron-800 hover:text-saffron-900 uppercase tracking-wider hover:underline"
              >
                ← Continue Shopping
              </Link>
            </div>
          </div>

          {/* Right Column: Order Summary (4 cols) */}
          <div className="lg:col-span-4 space-y-4">
            <div className="sticky top-24 rounded-2xl border border-spice-border bg-white p-5 sm:p-6 shadow-subtle">
              <h2 className="text-base font-bold font-display text-spice-black uppercase tracking-wider border-b border-spice-borderSubtle pb-3 mb-4">
                Order Summary
              </h2>

              {/* Price Breakdown */}
              <div className="space-y-2.5 text-xs">
                <div className="flex justify-between text-spice-stone">
                  <span>Items Subtotal</span>
                  <span className="font-semibold text-spice-black tabular-nums">
                    ₹{subtotal.toFixed(2)}
                  </span>
                </div>

                {discountAmount > 0 && (
                  <div className="flex justify-between text-emerald-700 font-semibold">
                    <span className="flex items-center gap-1">
                      <Sparkles className="h-3.5 w-3.5" />
                      Promo Discount ({appliedCouponCode})
                    </span>
                    <span className="tabular-nums">-₹{discountAmount.toFixed(2)}</span>
                  </div>
                )}

                <div className="flex justify-between text-spice-stone">
                  <span>Estimated Delivery</span>
                  <span className="font-semibold tabular-nums">
                    {shippingFee === 0 ? (
                      <span className="text-emerald-700 font-bold">FREE</span>
                    ) : (
                      `₹${shippingFee.toFixed(2)}`
                    )}
                  </span>
                </div>

                <div className="flex justify-between text-spice-muted text-[11px]">
                  <span>Statutory Taxes (GST)</span>
                  <span>Included in prices</span>
                </div>

                <div className="border-t border-spice-borderSubtle pt-3 flex justify-between text-sm font-bold text-spice-black">
                  <span>Grand Total</span>
                  <span className="text-xl font-extrabold text-spice-black tabular-nums">
                    ₹{finalTotal.toFixed(2)}
                  </span>
                </div>
              </div>

              {/* Coupon Redemption Block */}
              <div className="mt-5 pt-4 border-t border-spice-borderSubtle">
                {appliedCouponCode ? (
                  <div className="flex items-center justify-between rounded-xl border border-emerald-200 bg-emerald-50/70 p-3">
                    <div className="flex items-center gap-2">
                      <div className="h-6 w-6 rounded-md bg-emerald-600 text-white flex items-center justify-center">
                        <Check className="h-3.5 w-3.5" />
                      </div>
                      <div>
                        <span className="text-xs font-bold text-emerald-950 tracking-wider">
                          {appliedCouponCode}
                        </span>
                        <p className="text-[10px] text-emerald-700">Promo code applied</p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={removeCoupon}
                      disabled={isUpdating}
                      className="rounded-md p-1 text-spice-stone hover:text-red-600 transition-colors"
                      aria-label="Remove coupon"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                ) : (
                  <form onSubmit={handleApplyCoupon} className="flex gap-2">
                    <div className="relative flex-1">
                      <Tag className="absolute left-3 top-2.5 h-3.5 w-3.5 text-spice-muted" />
                      <input
                        type="text"
                        value={couponInput}
                        onChange={(e) => setCouponInput(e.target.value)}
                        placeholder="Coupon code"
                        className="w-full rounded-xl border border-spice-border bg-white py-2 pl-9 pr-3 text-xs uppercase tracking-wider placeholder:normal-case placeholder:tracking-normal focus:border-saffron-600 focus:outline-none focus:ring-2 focus:ring-saffron-500/20"
                      />
                    </div>
                    <Button
                      type="submit"
                      variant="outline"
                      size="sm"
                      disabled={!couponInput.trim() || isApplyingCoupon}
                      isLoading={isApplyingCoupon}
                      className="text-xs font-bold uppercase tracking-wider px-3.5 border-saffron-600"
                    >
                      Apply
                    </Button>
                  </form>
                )}
              </div>

              {/* Primary Checkout CTA */}
              <div className="mt-5">
                <Button
                  variant="primary"
                  size="lg"
                  isFullWidth
                  disabled={hasValidationIssues || items.length === 0}
                  onClick={() => router.push('/checkout')}
                  rightIcon={<ArrowRight className="h-4 w-4" />}
                  className="font-bold uppercase tracking-wider text-xs shadow-md"
                >
                  Proceed to Checkout • ₹{Math.round(finalTotal)}
                </Button>

                {hasValidationIssues && (
                  <p className="mt-2 text-center text-[11px] text-red-600 font-medium">
                    Resolve inventory notices above to checkout
                  </p>
                )}
              </div>

              {/* Security & Guarantee Badges */}
              <div className="mt-5 pt-4 border-t border-spice-borderSubtle space-y-2">
                <div className="flex items-center gap-2 text-[11px] text-spice-stone">
                  <ShieldCheck className="h-4 w-4 text-emerald-600 shrink-0" />
                  <span>Secure 256-bit encrypted checkout</span>
                </div>
                <div className="flex items-center gap-2 text-[11px] text-spice-stone">
                  <Check className="h-4 w-4 text-saffron-600 shrink-0" />
                  <span>100% Authentic Western Ghats origin guaranteed</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Mobile Sticky Checkout Bar */}
      <div className="fixed bottom-0 inset-x-0 bg-white/95 backdrop-blur-md border-t border-spice-border p-3 sm:hidden z-30 shadow-modal">
        <div className="flex items-center justify-between gap-3">
          <div>
            <span className="text-[10px] text-spice-muted uppercase tracking-wider font-semibold block">
              Total Payable
            </span>
            <span className="text-base font-extrabold text-spice-black tabular-nums">
              ₹{Math.round(finalTotal)}
            </span>
          </div>

          <Button
            variant="primary"
            size="md"
            disabled={hasValidationIssues || items.length === 0}
            onClick={() => router.push('/checkout')}
            rightIcon={<ArrowRight className="h-4 w-4" />}
            className="flex-1 font-bold text-xs uppercase tracking-wider"
          >
            Checkout ({itemCount})
          </Button>
        </div>
      </div>

      {/* Clear Cart Confirmation Modal */}
      <Modal
        isOpen={isClearModalOpen}
        onClose={() => setIsClearModalOpen(false)}
        title="Clear Entire Basket?"
        size="sm"
        footer={
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="md"
              className="flex-1"
              onClick={() => setIsClearModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              size="md"
              className="flex-1 bg-red-600 hover:bg-red-700 border-red-600"
              onClick={handleConfirmClear}
            >
              Clear Basket
            </Button>
          </div>
        }
      >
        <p className="text-xs text-spice-stone leading-relaxed">
          Are you sure you want to remove all {itemCount} items from your shopping basket?
          This action cannot be undone.
        </p>
      </Modal>
    </div>
  );
}
