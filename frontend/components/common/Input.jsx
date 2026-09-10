'use client';

import React, { forwardRef, useId } from 'react';

/**
 * Reusable accessible Input component for Bharat Masala.
 * Includes labels, error messages, helper text, left/right icons, and saffron focus rings.
 */
const Input = forwardRef(function Input(
  {
    label,
    error,
    helperText,
    leftIcon,
    rightIcon,
    id: providedId,
    name,
    type = 'text',
    placeholder = '',
    required = false,
    disabled = false,
    className = '',
    inputClassName = '',
    ...props
  },
  ref
) {
  const generatedId = useId();
  const inputId = providedId || (name ? `input-${name}` : generatedId);
  const errorId = `${inputId}-error`;
  const helperId = `${inputId}-helper`;

  const describedBy = error ? errorId : helperText ? helperId : undefined;

  return (
    <div className={`w-full ${className}`}>
      {label && (
        <label
          htmlFor={inputId}
          className="block text-xs font-semibold uppercase tracking-wider text-spice-stone mb-1.5"
        >
          {label}
          {required && <span className="text-feedback-error ml-1" aria-hidden="true">*</span>}
        </label>
      )}

      <div className="relative rounded-lg shadow-2xs">
        {leftIcon && (
          <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-spice-muted">
            {leftIcon}
          </div>
        )}

        <input
          ref={ref}
          id={inputId}
          name={name}
          type={type}
          disabled={disabled}
          required={required}
          placeholder={placeholder}
          aria-invalid={!!error}
          aria-describedby={describedBy}
          className={`
            w-full rounded-lg border bg-white px-3.5 py-2.5 text-sm text-spice-black placeholder:text-spice-muted/80
            transition-all duration-150 outline-none
            ${leftIcon ? 'pl-10' : 'pl-3.5'}
            ${rightIcon ? 'pr-10' : 'pr-3.5'}
            ${
              error
                ? 'border-feedback-error focus:border-feedback-error focus:ring-2 focus:ring-feedback-error/20 bg-red-50/20'
                : 'border-spice-border hover:border-spice-stone/50 focus:border-saffron-600 focus:ring-2 focus:ring-saffron-500/20'
            }
            ${disabled ? 'bg-spice-borderSubtle/60 text-spice-muted cursor-not-allowed border-spice-borderSubtle' : ''}
            ${inputClassName}
          `}
          {...props}
        />

        {rightIcon && (
          <div className="absolute inset-y-0 right-0 flex items-center pr-3 text-spice-muted">
            {rightIcon}
          </div>
        )}
      </div>

      {error ? (
        <p id={errorId} className="mt-1.5 text-xs text-feedback-error font-medium flex items-center gap-1" role="alert">
          <span>{error}</span>
        </p>
      ) : helperText ? (
        <p id={helperId} className="mt-1.5 text-xs text-spice-muted">
          {helperText}
        </p>
      ) : null}
    </div>
  );
});

export default Input;
