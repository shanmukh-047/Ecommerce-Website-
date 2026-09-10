'use client';

import React, { useEffect, useState } from 'react';
import { ArrowUp, MessageCircle } from 'lucide-react';

export default function FloatingActions() {
  const [showTop, setShowTop] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setShowTop(window.scrollY > 400);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <aside aria-label="Customer quick actions" className="fixed bottom-6 right-6 z-40 flex flex-col items-center gap-3">
      {/* WhatsApp Concierge */}
      <a
        href="https://wa.me/919876543210?text=Hello%20Bharat%20Masala,%20I'd%20like%20to%20inquire%20about%20your%20estate%20spices."
        target="_blank"
        rel="noopener noreferrer"
        aria-label="Chat with Bharat Masala customer support on WhatsApp"
        className="group relative flex items-center justify-center w-12 h-12 rounded-full bg-[#25D366] text-white shadow-lg hover:scale-105 active:scale-95 transition-all duration-200"
      >
        <MessageCircle className="h-6 w-6 fill-current" />
        <span className="sr-only">WhatsApp Concierge</span>
        <span className="pointer-events-none absolute right-14 whitespace-nowrap rounded-lg bg-spice-black px-3 py-1.5 text-xs font-semibold text-white shadow-md opacity-0 group-hover:opacity-100 transition-opacity duration-150">
          Chat with Spice Concierge
        </span>
      </a>

      {/* Back to Top */}
      {showTop && (
        <button
          type="button"
          onClick={scrollToTop}
          aria-label="Scroll back to top of page"
          className="flex items-center justify-center w-11 h-11 rounded-full bg-white border border-spice-border text-spice-stone hover:text-saffron-700 hover:border-saffron-500 shadow-md hover:scale-105 active:scale-95 transition-all duration-200"
        >
          <ArrowUp className="h-5 w-5" />
        </button>
      )}
    </aside>
  );
}
