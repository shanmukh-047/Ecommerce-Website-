'use client';

import React from 'react';
import { Minus, Plus, Trash2, Loader2 } from 'lucide-react';

/**
 * Reusable QuantitySelector stepper component for cart items and quick-add product cards.
 * Provides accessible controls, decrement-to-delete support, and loading states.
 */
export default function QuantitySelector({
  quantity = 1,
  onIncrement,
  onDecrement,
  min = 0,
  max = 99,
  disabled = false,
  isLoading = false,
  size = 'md',
  variant = 'solid-saffron',
  className = '',
}) {
  const isMin = quantity <= min;
  const isMax = quantity >= max;
  const isTrash = quantity === 1 && min === 0;

  const sizeStyles = {
    sm: 'h-8 px-1.5 text-xs min-w-[88px]',
    md: 'h-10 px-2 text-sm min-w-[108px]',
  };

  const btnSizeStyles = {
    sm: 'h-6 w-6',
    md: 'h-7 w-7',
  };

  const variantStyles = {
    'solid-saffron': 'bg-saffron-600 text-white shadow-xs border border-saffron-700/20',
    'outline': 'bg-white text-spice-black border border-spice-border shadow-xs',
    'dark': 'bg-spice-earth text-white border border-stone-800',
  };

  const btnVariantStyles = {
    'solid-saffron': 'hover:bg-saffron-700 active:bg-saffron-800 text-white disabled:opacity-40',
    'outline': 'hover:bg-spice-canvas active:bg-spice-borderSubtle text-spice-stone disabled:opacity-40',
    'dark': 'hover:bg-stone-800 active:bg-stone-900 text-white disabled:opacity-40',
  };

  return (
    <div
      className={`inline-flex items-center justify-between rounded-lg font-medium select-none ${
        sizeStyles[size] || sizeStyles.md
      } ${variantStyles[variant] || variantStyles['solid-saffron']} ${
        disabled ? 'opacity-50 cursor-not-allowed' : ''
      } ${className}`}
      role="group"
      aria-label="Quantity selector"
    >
      <button
        type="button"
        disabled={disabled || isMin || isLoading}
        onClick={onDecrement}
        aria-label={isTrash ? 'Remove item from cart' : 'Decrease quantity'}
        className={`inline-flex items-center justify-center rounded-md transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-saffron-400 ${
          btnSizeStyles[size] || btnSizeStyles.md
        } ${btnVariantStyles[variant] || btnVariantStyles['solid-saffron']}`}
      >
        {isTrash ? (
          <Trash2 className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        ) : (
          <Minus className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        )}
      </button>

      <span
        className="px-2 font-semibold tabular-nums text-center min-w-[24px]"
        aria-live="polite"
        aria-atomic="true"
      >
        {isLoading ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin mx-auto text-current" aria-hidden="true" />
        ) : (
          quantity
        )}
      </span>

      <button
        type="button"
        disabled={disabled || isMax || isLoading}
        onClick={onIncrement}
        aria-label="Increase quantity"
        className={`inline-flex items-center justify-center rounded-md transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-saffron-400 ${
          btnSizeStyles[size] || btnSizeStyles.md
        } ${btnVariantStyles[variant] || btnVariantStyles['solid-saffron']}`}
      >
        <Plus className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      </button>
    </div>
  );
}
