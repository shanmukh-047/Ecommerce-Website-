'use client';

import React from 'react';
import { ShoppingBag } from 'lucide-react';
import { useCart } from '../../context/CartContext';

/**
 * Dynamic Cart Indicator for the Header.
 * Displays real-time item count from backend cart state and triggers the Cart Drawer.
 */
export default function CartIndicator({ className = '' }) {
  const { itemCount, netSubtotal, openCart, isUpdating } = useCart();

  return (
    <button
      type="button"
      onClick={openCart}
      aria-label={`Shopping cart with ${itemCount} items, subtotal ₹${netSubtotal.toFixed(0)}`}
      className={`group relative flex items-center gap-2 rounded-xl p-2 text-spice-black hover:bg-spice-canvas transition-all duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-saffron-500 ${className}`}
    >
      <div className="relative flex items-center justify-center">
        <ShoppingBag
          className={`h-5 w-5 transition-transform group-hover:scale-110 text-spice-black group-hover:text-saffron-600 ${
            isUpdating ? 'animate-pulse' : ''
          }`}
          aria-hidden="true"
        />

        {itemCount > 0 && (
          <span
            className="absolute -top-1.5 -right-2 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-saffron-600 px-1 text-[10px] font-bold text-white shadow-xs animate-fadeIn tabular-nums"
            aria-live="polite"
          >
            {itemCount > 99 ? '99+' : itemCount}
          </span>
        )}
      </div>

      {/* Desktop subtotal label */}
      <div className="hidden xl:flex flex-col items-start text-left leading-none">
        <span className="text-[10px] uppercase font-bold tracking-wider text-spice-muted">
          Cart
        </span>
        <span className="text-xs font-semibold text-spice-black tabular-nums">
          ₹{netSubtotal.toFixed(0)}
        </span>
      </div>
    </button>
  );
}
