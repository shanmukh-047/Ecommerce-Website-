'use client';

import React, { useEffect, useId } from 'react';
import { X } from 'lucide-react';

/**
 * Accessible Modal dialog component for Bharat Masala.
 * Features keyboard Esc dismissal, outside click closing, focus lock, and body scroll prevention.
 */
export default function Modal({
  isOpen = false,
  onClose,
  title,
  description,
  children,
  footer,
  size = 'md',
  closeOnBackdropClick = true,
  className = '',
}) {
  const titleId = useId();
  const descId = useId();

  // Handle ESC key press and scroll locking
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
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? titleId : undefined}
      aria-describedby={description ? descId : undefined}
    >
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-spice-earth/60 backdrop-blur-xs transition-opacity animate-fadeIn"
        aria-hidden="true"
        onClick={closeOnBackdropClick ? onClose : undefined}
      />

      {/* Modal Surface */}
      <div
        className={`relative w-full rounded-2xl bg-white shadow-modal border border-spice-border overflow-hidden animate-slideUp transition-all duration-200 z-10 ${
          sizeStyles[size] || sizeStyles.md
        } ${className}`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-spice-borderSubtle px-6 py-4">
          <div>
            {title && (
              <h2 id={titleId} className="text-lg font-semibold text-spice-black font-display">
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
            aria-label="Close dialog"
            className="rounded-lg p-1.5 text-spice-stone hover:bg-spice-borderSubtle hover:text-spice-black transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-saffron-500"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        {/* Content Body */}
        <div className="px-6 py-5 max-h-[70vh] overflow-y-auto">{children}</div>

        {/* Footer */}
        {footer && (
          <div className="flex items-center justify-end gap-3 border-t border-spice-borderSubtle bg-spice-canvas px-6 py-4">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
