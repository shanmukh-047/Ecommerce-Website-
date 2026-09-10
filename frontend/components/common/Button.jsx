'use client';

import React from 'react';
import { Loader2 } from 'lucide-react';

/**
 * Reusable Button component for Bharat Masala.
 * Supports primary saffron, secondary cardamom, outline, ghost, and danger variants.
 * Accessible with keyboard focus, loading states, and minimum touch targets.
 */
export default function Button({
  children,
  type = 'button',
  variant = 'primary',
  size = 'md',
  isLoading = false,
  disabled = false,
  isFullWidth = false,
  leftIcon = null,
  rightIcon = null,
  className = '',
  onClick,
  ...props
}) {
  const baseStyles =
    'relative inline-flex items-center justify-center font-medium transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-55 active:scale-[0.98] select-none';

  const variantStyles = {
    primary:
      'bg-saffron-600 text-white hover:bg-saffron-700 active:bg-saffron-800 shadow-sm hover:shadow-saffron-glow focus-visible:ring-saffron-500 border border-saffron-700/20',
    secondary:
      'bg-cardamom-700 text-white hover:bg-cardamom-800 active:bg-cardamom-900 shadow-sm focus-visible:ring-cardamom-500 border border-cardamom-800/20',
    outline:
      'bg-transparent text-saffron-700 hover:bg-saffron-50 active:bg-saffron-100 border border-saffron-600 focus-visible:ring-saffron-500',
    'outline-stone':
      'bg-white text-spice-black hover:bg-spice-canvas active:bg-spice-border border border-spice-border hover:border-spice-stone/40 focus-visible:ring-saffron-500 shadow-xs',
    ghost:
      'bg-transparent text-spice-black hover:bg-spice-borderSubtle active:bg-spice-border focus-visible:ring-saffron-500',
    danger:
      'bg-feedback-error text-white hover:bg-red-700 active:bg-red-800 focus-visible:ring-red-500 shadow-sm',
    dark:
      'bg-spice-earth text-white hover:bg-stone-900 active:bg-black focus-visible:ring-stone-500 shadow-sm',
  };

  const sizeStyles = {
    sm: 'h-8 px-3 text-xs rounded-md gap-1.5 min-h-[32px]',
    md: 'h-10 px-4 text-sm rounded-lg gap-2 min-h-[40px]',
    lg: 'h-12 px-6 text-base rounded-lg gap-2.5 min-h-[48px]',
    icon: 'h-10 w-10 p-0 rounded-lg justify-center min-h-[40px] min-w-[40px]',
    'icon-sm': 'h-8 w-8 p-0 rounded-md justify-center min-h-[32px] min-w-[32px]',
  };

  const selectedVariant = variantStyles[variant] || variantStyles.primary;
  const selectedSize = sizeStyles[size] || sizeStyles.md;
  const widthClass = isFullWidth ? 'w-full' : '';

  const isDisabled = disabled || isLoading;

  return (
    <button
      type={type}
      disabled={isDisabled}
      aria-busy={isLoading}
      onClick={isDisabled ? undefined : onClick}
      className={`${baseStyles} ${selectedVariant} ${selectedSize} ${widthClass} ${className}`}
      {...props}
    >
      {isLoading ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin shrink-0 text-current" aria-hidden="true" />
          <span>{typeof children === 'string' ? children : 'Loading...'}</span>
        </>
      ) : (
        <>
          {leftIcon && <span className="inline-flex shrink-0 items-center">{leftIcon}</span>}
          <span>{children}</span>
          {rightIcon && <span className="inline-flex shrink-0 items-center">{rightIcon}</span>}
        </>
      )}
    </button>
  );
}
