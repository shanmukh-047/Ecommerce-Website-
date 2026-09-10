import React from 'react';

/**
 * Reusable Badge component for tags, discounts, pack sizes, stock states, and ratings.
 */
export default function Badge({
  children,
  variant = 'saffron',
  size = 'md',
  hasDot = false,
  className = '',
  ...props
}) {
  const baseStyles = 'inline-flex items-center font-medium select-none rounded-full tracking-wide';

  const variantStyles = {
    saffron: 'bg-saffron-100 text-saffron-900 border border-saffron-200/80',
    cardamom: 'bg-cardamom-100 text-cardamom-900 border border-cardamom-200/80',
    danger: 'bg-red-50 text-red-700 border border-red-200',
    success: 'bg-emerald-50 text-emerald-800 border border-emerald-200',
    warning: 'bg-amber-50 text-amber-800 border border-amber-200',
    stone: 'bg-spice-borderSubtle text-spice-stone border border-spice-border',
    dark: 'bg-spice-earth text-white border border-stone-800',
    outline: 'bg-transparent text-spice-black border border-spice-border',
    discount: 'bg-red-600 text-white font-bold tracking-wider shadow-xs',
  };

  const sizeStyles = {
    xs: 'text-[10px] leading-tight px-1.5 py-0.5 gap-1 font-semibold uppercase',
    sm: 'text-xs leading-none px-2 py-1 gap-1.5 font-medium',
    md: 'text-xs leading-none px-2.5 py-1.5 gap-1.5 font-semibold',
  };

  const dotColorStyles = {
    saffron: 'bg-saffron-500',
    cardamom: 'bg-cardamom-600',
    danger: 'bg-red-500',
    success: 'bg-emerald-500',
    warning: 'bg-amber-500',
    stone: 'bg-spice-muted',
    dark: 'bg-saffron-400',
    outline: 'bg-spice-stone',
    discount: 'bg-white',
  };

  const selectedVariant = variantStyles[variant] || variantStyles.saffron;
  const selectedSize = sizeStyles[size] || sizeStyles.md;
  const dotColor = dotColorStyles[variant] || 'bg-current';

  return (
    <span className={`${baseStyles} ${selectedVariant} ${selectedSize} ${className}`} {...props}>
      {hasDot && <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${dotColor}`} aria-hidden="true" />}
      <span>{children}</span>
    </span>
  );
}
