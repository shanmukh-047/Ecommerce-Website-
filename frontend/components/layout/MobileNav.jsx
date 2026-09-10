'use client';

import React from 'react';
import Link from 'next/link';
import { Home, Package, Layers, Sparkles, Building2, User, LogOut, Phone, ShieldCheck, ShoppingBag } from 'lucide-react';
import Drawer from '../common/Drawer';
import Badge from '../common/Badge';
import { useAuth } from '../../context/AuthContext';
import SearchInterface from './SearchInterface';

/**
 * Mobile Navigation Drawer component.
 * Provides accessible mobile-friendly access to catalog categories, search, and user account.
 */
export default function MobileNav({ isOpen, onClose }) {
  const { user, isAuthenticated, isWholesale, logout } = useAuth();

  const handleLogout = async () => {
    onClose();
    await logout();
  };

  const navLinks = [
    { href: '/', label: 'Home', icon: Home },
    { href: '/products', label: 'All Products / Shop', icon: Package },
    { href: '/cart', label: 'Shopping Basket', icon: ShoppingBag },
    { href: '/products?category=pure-spices', label: 'Pure Whole Spices', icon: Layers },
    { href: '/products?category=ground-spices', label: 'Fresh Ground Powders', icon: Layers },
    { href: '/products?category=signature-blends', label: 'Signature Blends & Masalas', icon: Sparkles },
    { href: '/products?tier=RESERVE', label: 'Reserve Single Origin', icon: ShieldCheck },
    { href: '/wholesale', label: 'Wholesale B2B Supply', icon: Building2 },
  ];

  return (
    <Drawer
      isOpen={isOpen}
      onClose={onClose}
      placement="left"
      size="sm"
      title="Bharat Masala"
      description="Western Ghats Spice Terroir"
    >
      <div className="flex flex-col gap-6">
        {/* Search Bar */}
        <div className="pt-1">
          <SearchInterface />
        </div>

        {/* User Account Status */}
        <div className="rounded-xl border border-spice-border bg-spice-canvas/80 p-3.5">
          {isAuthenticated ? (
            <div className="flex flex-col gap-2">
              <div className="flex items-center gap-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-saffron-100 text-xs font-bold text-saffron-800 border border-saffron-300">
                  {(user?.first_name?.[0] || user?.email?.[0] || 'U').toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-bold text-spice-black truncate">
                    {user?.full_name || user?.first_name || user?.email}
                  </p>
                  <p className="text-[10px] text-spice-muted truncate">{user?.email}</p>
                </div>
                {isWholesale && (
                  <Badge variant="cardamom" size="xs">
                    B2B
                  </Badge>
                )}
              </div>

              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-spice-borderSubtle">
                <Link
                  href="/account"
                  onClick={onClose}
                  className="rounded-lg bg-white border border-spice-border px-2.5 py-1.5 text-center text-xs font-medium text-spice-black hover:bg-spice-canvas"
                >
                  My Profile
                </Link>
                <Link
                  href="/account/orders"
                  onClick={onClose}
                  className="rounded-lg bg-white border border-spice-border px-2.5 py-1.5 text-center text-xs font-medium text-spice-black hover:bg-spice-canvas"
                >
                  Orders
                </Link>
              </div>

              <button
                type="button"
                onClick={handleLogout}
                className="flex items-center justify-center gap-1.5 text-xs text-red-600 hover:text-red-700 py-1"
              >
                <LogOut className="h-3.5 w-3.5" />
                <span>Sign Out</span>
              </button>
            </div>
          ) : (
            <div className="flex flex-col gap-2.5 text-center">
              <p className="text-xs text-spice-stone">
                Sign in to view orders, wholesale pricing, and saved addresses.
              </p>
              <div className="grid grid-cols-2 gap-2">
                <Link
                  href="/login"
                  onClick={onClose}
                  className="rounded-lg bg-saffron-600 px-3 py-2 text-center text-xs font-semibold text-white shadow-xs hover:bg-saffron-700"
                >
                  Sign In
                </Link>
                <Link
                  href="/register"
                  onClick={onClose}
                  className="rounded-lg border border-spice-border bg-white px-3 py-2 text-center text-xs font-semibold text-spice-black hover:bg-spice-canvas"
                >
                  Register
                </Link>
              </div>
            </div>
          )}
        </div>

        {/* Navigation Links */}
        <div>
          <p className="text-[11px] font-bold uppercase tracking-wider text-spice-muted mb-2 px-1">
            Navigation & Categories
          </p>
          <nav className="flex flex-col space-y-1">
            {navLinks.map((link) => {
              const Icon = link.icon;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={onClose}
                  className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-spice-black hover:bg-spice-canvas hover:text-saffron-700 transition-colors"
                >
                  <Icon className="h-4 w-4 text-spice-stone" />
                  <span>{link.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Help & Support Footer */}
        <div className="mt-auto border-t border-spice-borderSubtle pt-4 text-xs text-spice-stone">
          <p className="font-semibold text-spice-black mb-1 flex items-center gap-1.5">
            <Phone className="h-3.5 w-3.5 text-saffron-600" />
            <span>Customer Care</span>
          </p>
          <p className="text-spice-muted text-[11px]">Mon–Sat: 9:00 AM – 7:00 PM IST</p>
          <p className="text-spice-muted text-[11px] mt-0.5">Shimoga, Karnataka • PIN 577201</p>
        </div>
      </div>
    </Drawer>
  );
}
