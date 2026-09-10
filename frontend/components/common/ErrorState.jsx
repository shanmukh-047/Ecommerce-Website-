import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import Button from './Button';

/**
 * Reusable ErrorState component for network errors, API failures, and empty fallbacks.
 */
export default function ErrorState({
  title = 'Something went wrong',
  message = 'We encountered an issue fetching this data. Please try again.',
  onRetry,
  retryLabel = 'Try Again',
  secondaryAction = null,
  isRetrying = false,
  className = '',
}) {
  return (
    <div
      role="alert"
      className={`flex flex-col items-center justify-center p-8 sm:p-12 text-center rounded-2xl bg-white border border-red-100 shadow-subtle ${className}`}
    >
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-red-50 text-red-600 mb-4">
        <AlertTriangle className="h-7 w-7 stroke-[1.75]" aria-hidden="true" />
      </div>

      <h3 className="text-base sm:text-lg font-semibold text-spice-black font-display mb-1.5">
        {title}
      </h3>

      <p className="text-xs sm:text-sm text-spice-stone max-w-sm mb-6 leading-relaxed">
        {message}
      </p>

      <div className="flex flex-wrap items-center justify-center gap-3">
        {onRetry && (
          <Button
            variant="primary"
            size="md"
            onClick={onRetry}
            isLoading={isRetrying}
            leftIcon={<RefreshCw className="h-4 w-4" />}
          >
            {retryLabel}
          </Button>
        )}
        {secondaryAction}
      </div>
    </div>
  );
}
