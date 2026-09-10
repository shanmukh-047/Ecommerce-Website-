'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Menu, ChevronDown, Sparkles, ShieldCheck, Flame } from 'lucide-react';
import SearchInterface from './SearchInterface';
import AccountMenu from './AccountMenu';
import CartIndicator from './CartIndicator';
import MobileNav from './MobileNav';

const NAV_LINKS = [
  { href: '/', label: 'Home' },
  { href: '/products', label: 'Shop Spices' },
  {
    href: '/products',
    label: 'Categories',
    hasDropdown: true,
    children: [
      {
        href: '/products?category=pure-spices',
        label: 'Pure Whole Spices',
        desc: 'Malabar pepper, green cardamom, cloves',
        icon: ShieldCheck,
      },
      {
        href: '/products?category=ground-spices',
        label: 'Freshly Ground Powders',
        desc: 'High-curcumin turmeric, roasted coriander',
        icon: Flame,
      },
      {
        href: '/products?category=signature-blends',
        label: 'Signature Blends & Masalas',
        desc: 'Garam masala, Malenadu sambar blend',
        icon: Sparkles,
      },
      {
        href: '/products?tier=RESERVE',
        label: 'Reserve Single Origin',
        desc: 'Hand-picked boldest grade estate harvests',
        icon: Sparkles,
      },
    ],
  },
  { href: '/about', label: 'Our Terroir' },
  { href: '/track', label: 'Track Order' },
  { href: '/wholesale', label: 'Wholesale B2B' },
];

/**
 * Global responsive Header component for Bharat Masala.
 * Sticky header with announcement banner, search, authentication menu, and live cart indicator.
 */
export default function Header() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [categoryDropdownOpen, setCategoryDropdownOpen] = useState(false);
  const [isScrolled, setIsScrolled] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Close category dropdown on route change
  useEffect(() => {
    setCategoryDropdownOpen(false);
  }, [pathname]);

  return (
    <>
      <header className="sticky top-0 z-40 w-full transition-all duration-200">
        {/* Top Announcement Bar */}
        <div className="bg-spice-earth text-white text-[11px] font-medium py-1.5 px-4 text-center tracking-wide border-b border-white/10 hidden sm:block">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <span className="text-spice-muted">
              Origin: Western Ghats, Karnataka &amp; Kerala
            </span>
            <div className="flex items-center gap-2">
              <span className="text-saffron-400 font-semibold">Free Delivery</span>
              <span>on all prepaid orders above ₹499</span>
            </div>
            <Link
              href="/wholesale"
              className="text-stone-300 hover:text-white underline underline-offset-2 transition-colors"
            >
              Wholesale &amp; Bulk Inquiry
            </Link>
          </div>
        </div>

        {/* Main Navbar */}
        <div
          className={`w-full transition-all duration-200 ${
            isScrolled
              ? 'glass shadow-subtle py-2.5 sm:py-3'
              : 'bg-white/95 backdrop-blur-md border-b border-spice-border py-3 sm:py-4'
          }`}
        >
          <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center justify-between gap-4">
            {/* Left: Mobile hamburger & Brand Logo */}
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setMobileNavOpen(true)}
                aria-label="Open mobile navigation menu"
                className="lg:hidden rounded-lg p-2 text-spice-black hover:bg-spice-canvas focus:outline-none focus-visible:ring-2 focus-visible:ring-saffron-500"
              >
                <Menu className="h-5 w-5" aria-hidden="true" />
              </button>

              <Link
                href="/"
                className="flex items-center gap-2 font-display text-xl sm:text-2xl font-bold tracking-tight text-spice-black focus:outline-none focus-visible:ring-2 focus-visible:ring-saffron-500 rounded-md"
              >
                <span className="inline-flex h-7 w-7 items-center justify-center rounded-lg bg-saffron-600 text-white font-serif text-sm shadow-2xs">
                  B
                </span>
                <span>
                  BHARAT <span className="text-saffron-600 font-normal italic">MASALA</span>
                </span>
              </Link>
            </div>

            {/* Center Desktop Navigation */}
            <nav className="hidden lg:flex items-center gap-6 text-xs font-semibold uppercase tracking-wider text-spice-stone">
              {NAV_LINKS.map((link) => {
                const isActive = pathname === link.href;

                if (link.hasDropdown) {
                  return (
                    <div
                      key={link.label}
                      className="relative"
                      onMouseEnter={() => setCategoryDropdownOpen(true)}
                      onMouseLeave={() => setCategoryDropdownOpen(false)}
                    >
                      <button
                        type="button"
                        onClick={() => setCategoryDropdownOpen(!categoryDropdownOpen)}
                        className={`flex items-center gap-1 py-2 hover:text-saffron-700 transition-colors ${
                          isActive ? 'text-saffron-700 font-bold' : ''
                        }`}
                      >
                        <span>{link.label}</span>
                        <ChevronDown className="h-3.5 w-3.5" />
                      </button>

                      {categoryDropdownOpen && (
                        <div className="absolute left-0 top-full mt-1 w-72 rounded-2xl bg-white border border-spice-border shadow-modal p-2 z-50 animate-slideUp">
                          {link.children.map((child) => {
                            const Icon = child.icon;
                            return (
                              <Link
                                key={child.href}
                                href={child.href}
                                onClick={() => setCategoryDropdownOpen(false)}
                                className="flex items-start gap-3 p-2.5 rounded-xl hover:bg-spice-canvas group transition-colors"
                              >
                                <div className="p-2 rounded-lg bg-saffron-50 text-saffron-700 group-hover:bg-saffron-600 group-hover:text-white transition-colors shrink-0">
                                  <Icon className="h-4 w-4" />
                                </div>
                                <div className="flex-1 min-w-0">
                                  <p className="text-xs font-bold normal-case text-spice-black group-hover:text-saffron-700">
                                    {child.label}
                                  </p>
                                  <p className="text-[11px] normal-case text-spice-muted truncate mt-0.5">
                                    {child.desc}
                                  </p>
                                </div>
                              </Link>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                }

                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={`py-2 hover:text-saffron-700 transition-colors ${
                      isActive ? 'text-saffron-700 font-bold' : ''
                    }`}
                  >
                    {link.label}
                  </Link>
                );
              })}
            </nav>

            {/* Center-Right Search Bar (Desktop) */}
            <div className="hidden md:block flex-1 max-w-xs xl:max-w-sm">
              <SearchInterface />
            </div>

            {/* Right: Account & Cart Indicator */}
            <div className="flex items-center gap-2 sm:gap-3">
              <AccountMenu />
              <div className="h-5 w-px bg-spice-border hidden sm:block" />
              <CartIndicator />
            </div>
          </div>

          {/* Mobile Search Bar below header */}
          <div className="md:hidden px-4 pt-2.5 pb-1">
            <SearchInterface />
          </div>
        </div>

        {/* Signature spice trail line */}
        <div className="spice-trail" />
      </header>

      {/* Mobile Navigation Drawer */}
      <MobileNav isOpen={mobileNavOpen} onClose={() => setMobileNavOpen(false)} />
    </>
  );
}
