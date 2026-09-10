'use client';

import React, { useEffect, useId } from 'react';
import { X } from 'lucide-react';

/**
 * Reusable Drawer component for slide-over sidebars (Cart, Filters, Mobile Navigation).
 * Handles accessible keyboard navigation, scroll locking, and smooth transitions.
 */
export default function Drawer({
  isOpen = false,
  onClose,
  title,
  description,
  children,
  footer,
  placement = 'right',
  size = 'md',
  className = '',
}) {
  const titleId = useId();
  const descId = useId();

  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose?.();
      }
    };

    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      document.body.style.overflow = originalOverflow;
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const sizeStyles = {
    sm: placement === 'bottom' ? 'max-h-[60vh]' : 'max-w-xs',
    md: placement === 'bottom' ? 'max-h-[80vh]' : 'max-w-md',
    lg: placement === 'bottom' ? 'max-h-[90vh]' : 'max-w-xl',
  };

  const placementStyles = {
    right: 'inset-y-0 right-0 animate-slideLeft',
    left: 'inset-y-0 left-0',
    bottom: 'inset-x-0 bottom-0 rounded-t-2xl animate-slideUp',
  };

  return (
    <div
      className="fixed inset-0 z-50 overflow-hidden"
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? titleId : undefined}
      aria-describedby={description ? descId : undefined}
    >
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-spice-earth/60 backdrop-blur-xs transition-opacity animate-fadeIn"
        aria-hidden="true"
        onClick={onClose}
      />

      {/* Drawer Surface */}
      <div
        className={`fixed flex flex-col bg-white shadow-drawer border-l border-spice-border w-full ${
          placementStyles[placement] || placementStyles.right
        } ${sizeStyles[size] || sizeStyles.md} ${className}`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-spice-borderSubtle px-5 py-4 shrink-0 bg-white">
          <div>
            {title && (
              <h2 id={titleId} className="text-base font-semibold text-spice-black font-display">
                {title}
              </h2>
            )}
            {description && (
              <p id={descId} className="text-xs text-spice-stone mt-0.5">
                {description}
              </p>
            )}
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close drawer"
            className="rounded-lg p-1.5 text-spice-stone hover:bg-spice-borderSubtle hover:text-spice-black transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-saffron-500"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto px-5 py-4">{children}</div>

        {/* Sticky Footer */}
        {footer && (
          <div className="border-t border-spice-borderSubtle bg-spice-canvas/80 backdrop-blur-xs px-5 py-4 shrink-0">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
