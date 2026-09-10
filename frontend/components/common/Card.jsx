import React from 'react';

/**
 * Reusable Card container component with clean white surface, subtle border, and optional hover elevation.
 */
export default function Card({
  children,
  variant = 'default',
  interactive = false,
  padding = 'md',
  className = '',
  onClick,
  ...props
}) {
  const baseStyles = 'rounded-xl transition-all duration-200';

  const variantStyles = {
    default: 'bg-white border border-spice-border shadow-subtle',
    flat: 'bg-spice-borderSubtle/50 border border-spice-border/60',
    elevated: 'bg-white border border-spice-border/80 shadow-card',
    dark: 'bg-spice-earth text-white border border-stone-800 shadow-card',
  };

  const interactiveStyles = interactive
    ? 'cursor-pointer hover:-translate-y-1 hover:shadow-card-hover hover:border-saffron-500/40 active:translate-y-0 active:shadow-subtle'
    : '';

  const paddingStyles = {
    none: 'p-0',
    sm: 'p-3 sm:p-4',
    md: 'p-4 sm:p-5',
    lg: 'p-6 sm:p-8',
  };

  const selectedVariant = variantStyles[variant] || variantStyles.default;
  const selectedPadding = paddingStyles[padding] || paddingStyles.md;

  return (
    <div
      onClick={onClick}
      className={`${baseStyles} ${selectedVariant} ${interactiveStyles} ${selectedPadding} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}
