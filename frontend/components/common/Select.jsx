'use client';

import React, { forwardRef, useId } from 'react';
import { ChevronDown } from 'lucide-react';

/**
 * Reusable accessible Select dropdown component for Bharat Masala.
 * Features custom dropdown chevron, error states, and responsive styling.
 */
const Select = forwardRef(function Select(
  {
    label,
    options = [],
    value,
    onChange,
    error,
    helperText,
    id: providedId,
    name,
    required = false,
    disabled = false,
    placeholder = 'Select an option',
    className = '',
    selectClassName = '',
    children,
    ...props
  },
  ref
) {
  const generatedId = useId();
  const selectId = providedId || (name ? `select-${name}` : generatedId);
  const errorId = `${selectId}-error`;
  const helperId = `${selectId}-helper`;

  const describedBy = error ? errorId : helperText ? helperId : undefined;

  return (
    <div className={`w-full ${className}`}>
      {label && (
        <label
          htmlFor={selectId}
          className="block text-xs font-semibold uppercase tracking-wider text-spice-stone mb-1.5"
        >
          {label}
          {required && <span className="text-feedback-error ml-1" aria-hidden="true">*</span>}
        </label>
      )}

      <div className="relative rounded-lg shadow-2xs">
        <select
          ref={ref}
          id={selectId}
          name={name}
          value={value}
          onChange={onChange}
          disabled={disabled}
          required={required}
          aria-invalid={!!error}
          aria-describedby={describedBy}
          className={`
            w-full appearance-none rounded-lg border bg-white px-3.5 py-2.5 pr-10 text-sm text-spice-black
            transition-all duration-150 outline-none cursor-pointer
            ${
              error
                ? 'border-feedback-error focus:border-feedback-error focus:ring-2 focus:ring-feedback-error/20 bg-red-50/20'
                : 'border-spice-border hover:border-spice-stone/50 focus:border-saffron-600 focus:ring-2 focus:ring-saffron-500/20'
            }
            ${disabled ? 'bg-spice-borderSubtle/60 text-spice-muted cursor-not-allowed border-spice-borderSubtle' : ''}
            ${selectClassName}
          `}
          {...props}
        >
          {placeholder && (
            <option value="" disabled className="text-spice-muted">
              {placeholder}
            </option>
          )}

          {children
            ? children
            : options.map((opt) => (
                <option key={opt.value} value={opt.value} disabled={opt.disabled}>
                  {opt.label}
                </option>
              ))}
        </select>

        <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3 text-spice-stone">
          <ChevronDown className="h-4 w-4" aria-hidden="true" />
        </div>
      </div>

      {error ? (
        <p id={errorId} className="mt-1.5 text-xs text-feedback-error font-medium" role="alert">
          {error}
        </p>
      ) : helperText ? (
        <p id={helperId} className="mt-1.5 text-xs text-spice-muted">
          {helperText}
        </p>
      ) : null}
    </div>
  );
});

export default Select;
