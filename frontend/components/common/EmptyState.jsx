import React from 'react';
import { PackageOpen } from 'lucide-react';

/**
 * Reusable EmptyState component for zero-state screens (empty cart, search, orders, wishlist).
 */
export default function EmptyState({
  icon,
  title = 'No items found',
  description = 'There are currently no items to display.',
  action = null,
  className = '',
}) {
  return (
    <div
      className={`flex flex-col items-center justify-center p-8 sm:p-12 text-center rounded-2xl bg-white border border-dashed border-spice-border ${className}`}
    >
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-saffron-50 text-saffron-700 mb-4 shadow-2xs">
        {icon || <PackageOpen className="h-8 w-8 stroke-[1.5]" aria-hidden="true" />}
      </div>

      <h3 className="text-base sm:text-lg font-semibold text-spice-black font-display mb-1.5">
        {title}
      </h3>

      <p className="text-xs sm:text-sm text-spice-stone max-w-sm mb-6 leading-relaxed">
        {description}
      </p>

      {action && <div className="inline-flex items-center">{action}</div>}
    </div>
  );
}
