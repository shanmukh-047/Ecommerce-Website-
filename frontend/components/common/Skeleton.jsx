import React from 'react';

/**
 * Reusable accessible Skeleton component for loading shimmers.
 */
export default function Skeleton({
  variant = 'rect',
  width,
  height,
  className = '',
  ...props
}) {
  const variantStyles = {
    text: 'h-4 w-full rounded-sm',
    circle: 'rounded-full',
    rect: 'rounded-lg',
  };

  const style = {
    ...(width ? { width } : {}),
    ...(height ? { height } : {}),
  };

  return (
    <div
      aria-hidden="true"
      style={style}
      className={`shimmer-bg ${variantStyles[variant] || variantStyles.rect} ${className}`}
      {...props}
    />
  );
}

/**
 * Pre-composed Skeleton for ProductCard
 */
export function ProductCardSkeleton() {
  return (
    <div
      aria-hidden="true"
      className="flex flex-col rounded-xl bg-white border border-spice-border p-3.5 sm:p-4"
    >
      {/* Square image skeleton */}
      <Skeleton height="180px" className="w-full mb-3 rounded-lg" />

      {/* Category line */}
      <Skeleton height="12px" width="40%" className="mb-2" />

      {/* Title lines */}
      <Skeleton height="16px" width="85%" className="mb-1.5" />
      <Skeleton height="16px" width="60%" className="mb-3" />

      {/* Terroir / subtitle */}
      <Skeleton height="12px" width="50%" className="mb-4" />

      {/* Footer price & button */}
      <div className="pt-2 border-t border-spice-borderSubtle flex items-center justify-between mt-auto">
        <Skeleton height="20px" width="70px" />
        <Skeleton height="32px" width="64px" className="rounded-md" />
      </div>
    </div>
  );
}

/**
 * Pre-composed Skeleton for Cart Items
 */
export function CartItemSkeleton() {
  return (
    <div
      aria-hidden="true"
      className="flex items-center gap-3 py-3 border-b border-spice-borderSubtle"
    >
      <Skeleton height="64px" width="64px" className="rounded-lg shrink-0" />
      <div className="flex-1 min-w-0">
        <Skeleton height="14px" width="75%" className="mb-1.5" />
        <Skeleton height="12px" width="40%" className="mb-2" />
        <Skeleton height="16px" width="50px" />
      </div>
      <Skeleton height="32px" width="80px" className="rounded-md shrink-0" />
    </div>
  );
}
