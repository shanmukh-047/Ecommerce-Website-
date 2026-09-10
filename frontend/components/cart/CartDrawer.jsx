'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { ShoppingBag, ArrowRight, Tag, X, Check, Truck, Trash2, AlertTriangle } from 'lucide-react';
import Drawer from '../common/Drawer';
import Button from '../common/Button';
import QuantitySelector from '../common/QuantitySelector';
import EmptyState from '../common/EmptyState';
import { useCart } from '../../context/CartContext';

const FREE_SHIPPING_THRESHOLD = 499;

/**
 * Production Cart Drawer component for Bharat Masala.
 * Synchronized with the Django backend cart engine, coupon application,
 * free shipping progress bar, instant quantity steppers, and validation alerts.
 */
export default function CartDrawer() {
  const {
    isCartOpen,
    closeCart,
    items,
    itemCount,
    subtotal,
    discountAmount,
    netSubtotal,
    appliedCouponCode,
    validationIssuesMap,
    hasValidationIssues,
    updateQuantity,
    removeItem,
    applyCoupon,
    removeCoupon,
    isUpdating,
    isItemUpdating,
  } = useCart();

  const [couponInput, setCouponInput] = useState('');
  const [isApplyingCoupon, setIsApplyingCoupon] = useState(false);

  const amountNeededForFreeShipping = Math.max(0, FREE_SHIPPING_THRESHOLD - subtotal);
  const freeShippingProgress = Math.min(100, Math.round((subtotal / FREE_SHIPPING_THRESHOLD) * 100));

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

  return (
    <Drawer
      isOpen={isCartOpen}
      onClose={closeCart}
      placement="right"
      size="md"
      title={`Your Basket (${itemCount})`}
      description="Fresh spices from Western Ghats"
      footer={
        items.length > 0 ? (
          <div className="flex flex-col gap-2.5 w-full">
            {/* Bill Summary */}
            <div className="space-y-1.5 text-xs">
              <div className="flex justify-between text-spice-stone">
                <span>Items Subtotal</span>
                <span className="font-semibold text-spice-black tabular-nums">
                  ₹{subtotal.toFixed(2)}
                </span>
              </div>

              {discountAmount > 0 && (
                <div className="flex justify-between text-emerald-700 font-medium">
                  <span>Coupon Discount ({appliedCouponCode})</span>
                  <span className="tabular-nums">-₹{discountAmount.toFixed(2)}</span>
                </div>
              )}

              <div className="flex justify-between text-spice-stone">
                <span>Shipping &amp; Handling</span>
                <span className="font-medium text-emerald-700">
                  {amountNeededForFreeShipping === 0 ? 'FREE' : '₹50.00'}
                </span>
              </div>

              <div className="border-t border-spice-borderSubtle pt-2 flex justify-between text-sm font-bold text-spice-black">
                <span>Total Amount</span>
                <span className="text-base font-bold tabular-nums">
                  ₹{(amountNeededForFreeShipping === 0 ? netSubtotal : netSubtotal + 50).toFixed(2)}
                </span>
              </div>
              <p className="text-[10px] text-spice-muted text-right">
                Includes all applicable GST &amp; Taxes
              </p>
            </div>

            {/* Checkout CTA */}
            <Link href="/checkout" onClick={closeCart} className="w-full">
              <Button
                variant="primary"
                size="lg"
                isFullWidth
                disabled={hasValidationIssues}
                rightIcon={<ArrowRight className="h-4 w-4" />}
                className="font-semibold uppercase tracking-wider text-xs"
              >
                Proceed to Checkout • ₹
                {(amountNeededForFreeShipping === 0 ? netSubtotal : netSubtotal + 50).toFixed(0)}
              </Button>
            </Link>

            {/* View Full Cart Page Link */}
            <Link href="/cart" onClick={closeCart} className="w-full text-center">
              <span className="text-xs font-bold text-saffron-800 hover:text-saffron-900 uppercase tracking-wider block py-1 hover:underline">
                View Full Basket &amp; Details →
              </span>
            </Link>
          </div>
        ) : null
      }
    >
      {items.length === 0 ? (
        <EmptyState
          icon={<ShoppingBag className="h-8 w-8 stroke-[1.5]" />}
          title="Your basket is empty"
          description="Fill your kitchen with authentic, single-origin Western Ghats spices, fresh ground masalas, and whole seeds."
          action={
            <Link href="/products" onClick={closeCart}>
              <Button variant="primary" size="md">
                Explore Spices
              </Button>
            </Link>
          }
        />
      ) : (
        <div className="flex flex-col gap-4">
          {/* Validation Notice if issues exist */}
          {hasValidationIssues && (
            <div className="rounded-xl border border-amber-300 bg-amber-50 p-2.5 text-amber-900 text-xs flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
              <span>Some items have limited stock. Please adjust quantities to checkout.</span>
            </div>
          )}

          {/* Free Shipping Progress Indicator */}
          <div className="rounded-xl border border-spice-borderSubtle bg-spice-canvas/80 p-3">
            <div className="flex items-center gap-2 text-xs font-semibold text-spice-black mb-1.5">
              <Truck className="h-4 w-4 text-saffron-600 shrink-0" />
              {amountNeededForFreeShipping === 0 ? (
                <span className="text-emerald-700 font-bold">
                  You have unlocked FREE delivery across India!
                </span>
              ) : (
                <span>
                  Add <strong className="text-saffron-700 font-bold">₹{amountNeededForFreeShipping.toFixed(0)}</strong> more to get FREE Delivery
                </span>
              )}
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-spice-border">
              <div
                className="h-full bg-saffron-600 transition-all duration-300 rounded-full"
                style={{ width: `${freeShippingProgress}%` }}
              />
            </div>
          </div>

          {/* Cart Items List */}
          <div className="divide-y divide-spice-borderSubtle">
            {items.map((item) => {
              const unitPrice = parseFloat(item.unit_price || 0);
              const lineTotal = parseFloat(item.line_total || 0);
              const isUpdatingThis = isItemUpdating(item.id);
              const issueCode = validationIssuesMap[item.id];

              return (
                <div
                  key={item.id}
                  className={`py-3 flex items-start gap-3 transition-opacity ${
                    isUpdatingThis ? 'opacity-60' : 'opacity-100'
                  }`}
                >
                  <div className="h-14 w-14 rounded-lg bg-spice-canvas border border-spice-border overflow-hidden shrink-0 flex items-center justify-center text-spice-muted">
                    <ShoppingBag className="h-6 w-6 stroke-[1.2]" />
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-1">
                      <h4 className="text-xs font-semibold text-spice-black truncate">
                        {item.product_name}
                      </h4>
                      <button
                        type="button"
                        onClick={() => removeItem(item.id)}
                        disabled={isUpdating}
                        className="text-spice-muted hover:text-red-600 p-0.5 transition-colors"
                        aria-label="Remove item"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>

                    <p className="text-[11px] text-spice-muted mt-0.5 truncate">
                      {item.variant_name || `${item.weight_in_grams}g`} • ₹{unitPrice.toFixed(0)} each
                    </p>

                    {issueCode && (
                      <span className="inline-block mt-1 text-[10px] font-bold text-red-600 bg-red-50 px-1.5 py-0.5 rounded">
                        Insufficient stock
                      </span>
                    )}

                    <div className="flex items-center justify-between mt-2">
                      <QuantitySelector
                        quantity={item.quantity}
                        min={0}
                        size="sm"
                        onIncrement={() => updateQuantity(item.id, item.quantity + 1)}
                        onDecrement={() => updateQuantity(item.id, item.quantity - 1)}
                        disabled={isUpdating}
                      />

                      <span className="text-xs font-bold text-spice-black tabular-nums">
                        ₹{lineTotal.toFixed(0)}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Coupon / Promo Code Block */}
          <div className="pt-2 border-t border-spice-borderSubtle">
            {appliedCouponCode ? (
              <div className="flex items-center justify-between rounded-xl border border-emerald-200 bg-emerald-50/60 p-2.5">
                <div className="flex items-center gap-2">
                  <div className="h-6 w-6 rounded-md bg-emerald-600 text-white flex items-center justify-center">
                    <Check className="h-3.5 w-3.5" />
                  </div>
                  <div>
                    <span className="text-xs font-bold text-emerald-900 tracking-wider">
                      {appliedCouponCode}
                    </span>
                    <p className="text-[10px] text-emerald-700">
                      Savings applied to this order
                    </p>
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
                    placeholder="Enter coupon code"
                    className="w-full rounded-lg border border-spice-border bg-white py-1.5 pl-8 pr-3 text-xs uppercase tracking-wider placeholder:normal-case placeholder:tracking-normal focus:border-saffron-600 focus:outline-none focus:ring-1 focus:ring-saffron-500"
                  />
                </div>
                <Button
                  type="submit"
                  variant="outline"
                  size="sm"
                  disabled={!couponInput.trim() || isApplyingCoupon}
                  isLoading={isApplyingCoupon}
                  className="text-xs font-semibold px-3 uppercase"
                >
                  Apply
                </Button>
              </form>
            )}
          </div>
        </div>
      )}
    </Drawer>
  );
}
