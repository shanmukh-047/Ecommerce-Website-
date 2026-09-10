'use client';

import React, { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { User, LogOut, Package, MapPin, Building2, ChevronDown } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../common/Toast';
import Badge from '../common/Badge';

/**
 * Dynamic Account Menu in the Header.
 * Displays real-time authentication status, user role badges, and account navigation.
 */
export default function AccountMenu({ className = '' }) {
  const { user, isAuthenticated, isWholesale, isLoading, logout } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  const { success } = useToast();

  // Close on outside click
  useEffect(() => {
    const handleOutsideClick = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };

    const handleEsc = (e) => {
      if (e.key === 'Escape') setIsOpen(false);
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleOutsideClick);
      document.addEventListener('keydown', handleEsc);
    }
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
      document.removeEventListener('keydown', handleEsc);
    };
  }, [isOpen]);

  const handleLogout = async () => {
    setIsOpen(false);
    await logout();
    success('You have been signed out successfully.', 'Signed Out');
  };

  if (isLoading) {
    return (
      <div className="h-9 w-9 rounded-xl bg-spice-borderSubtle animate-pulse" aria-hidden="true" />
    );
  }

  // Guest State
  if (!isAuthenticated) {
    return (
      <div className="flex items-center gap-1.5">
        <Link
          href="/login"
          className="inline-flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-semibold uppercase tracking-wider text-spice-black hover:bg-spice-canvas hover:text-saffron-600 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-saffron-500"
        >
          <User className="h-4 w-4" aria-hidden="true" />
          <span>Sign In</span>
        </Link>
      </div>
    );
  }

  // Authenticated State
  const displayName = user?.first_name || user?.full_name || user?.email?.split('@')[0] || 'My Account';
  const initial = (displayName[0] || 'U').toUpperCase();

  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-haspopup="menu"
        aria-label={`User account menu for ${displayName}`}
        className="flex items-center gap-2 rounded-xl p-1.5 text-spice-black hover:bg-spice-canvas transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-saffron-500"
      >
        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-saffron-100 text-xs font-bold text-saffron-800 border border-saffron-300/60 shadow-2xs">
          {initial}
        </div>

        <div className="hidden md:flex flex-col items-start text-left leading-tight">
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-semibold text-spice-black max-w-[110px] truncate">
              {displayName}
            </span>
            {isWholesale && (
              <Badge variant="cardamom" size="xs">
                B2B
              </Badge>
            )}
          </div>
          <span className="text-[10px] text-spice-muted">Account</span>
        </div>

        <ChevronDown
          className={`hidden md:block h-3.5 w-3.5 text-spice-stone transition-transform duration-200 ${
            isOpen ? 'rotate-180' : ''
          }`}
          aria-hidden="true"
        />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div
          role="menu"
          className="absolute right-0 mt-2 w-60 rounded-xl bg-white border border-spice-border shadow-modal p-1.5 z-50 animate-slideUp text-sm focus:outline-none"
        >
          {/* User info banner */}
          <div className="px-3 py-2.5 border-b border-spice-borderSubtle bg-spice-canvas/50 rounded-lg mb-1">
            <p className="text-xs font-bold text-spice-black truncate">{user?.full_name || displayName}</p>
            <p className="text-[11px] text-spice-muted truncate mt-0.5">{user?.email}</p>
            {isWholesale && (
              <div className="mt-1.5">
                <Badge variant="cardamom" size="xs">
                  Verified Wholesale Buyer
                </Badge>
              </div>
            )}
          </div>

          <Link
            href="/account"
            role="menuitem"
            onClick={() => setIsOpen(false)}
            className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-spice-black hover:bg-spice-canvas hover:text-saffron-700 transition-colors text-xs font-medium"
          >
            <User className="h-4 w-4 text-spice-stone" />
            <span>Profile & Settings</span>
          </Link>

          <Link
            href="/account/orders"
            role="menuitem"
            onClick={() => setIsOpen(false)}
            className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-spice-black hover:bg-spice-canvas hover:text-saffron-700 transition-colors text-xs font-medium"
          >
            <Package className="h-4 w-4 text-spice-stone" />
            <span>My Orders & Invoices</span>
          </Link>

          <Link
            href="/account/addresses"
            role="menuitem"
            onClick={() => setIsOpen(false)}
            className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-spice-black hover:bg-spice-canvas hover:text-saffron-700 transition-colors text-xs font-medium"
          >
            <MapPin className="h-4 w-4 text-spice-stone" />
            <span>Delivery Addresses</span>
          </Link>

          {isWholesale && (
            <Link
              href="/wholesale"
              role="menuitem"
              onClick={() => setIsOpen(false)}
              className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-spice-black hover:bg-spice-canvas hover:text-cardamom-700 transition-colors text-xs font-medium"
            >
              <Building2 className="h-4 w-4 text-cardamom-600" />
              <span>Wholesale Bulk Pricing</span>
            </Link>
          )}

          <div className="my-1 border-t border-spice-borderSubtle" />

          <button
            type="button"
            role="menuitem"
            onClick={handleLogout}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-red-600 hover:bg-red-50 transition-colors text-xs font-medium text-left"
          >
            <LogOut className="h-4 w-4 text-red-500" />
            <span>Sign Out</span>
          </button>
        </div>
      )}
    </div>
  );
}
