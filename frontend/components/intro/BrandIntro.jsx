'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Sparkles, ShieldCheck, Sun, Mountain, ArrowRight, Clock } from 'lucide-react';

/**
 * BrandIntro - Polished ~10-Second Animated Brand Reveal for Bharat Masala
 * 
 * Features:
 * - Exact ~10-second deterministic runtime with smooth progress bar
 * - 3-phase narrative reveal: Terroir -> Heritage Brand -> 4 Purity Pillars
 * - Ambient warm spice ember / aroma particle visuals (pure CSS)
 * - Accessible "Skip to Sign In" control & Escape key support
 * - Prefers-reduced-motion support
 * - Zero backend network calls or duplicate requests
 * - Deterministic timer cleanup to prevent memory/lifecycle leaks
 */
export default function BrandIntro({ onComplete }) {
  const [elapsed, setElapsed] = useState(0); // 0 to 10 seconds
  const [phase, setPhase] = useState(1); // 1: Terroir (0-3s), 2: Brand (3-6.5s), 3: Pillars (6.5-10s)
  const startTimeRef = useRef(Date.now());

  useEffect(() => {
    // Check if user prefers reduced motion
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) {
      // For reduced motion, complete after 1.5s gentle reveal
      const t = setTimeout(() => {
        if (onComplete) onComplete();
      }, 1500);
      return () => clearTimeout(t);
    }

    // 100ms interval ticker for smooth 10s progress
    const interval = setInterval(() => {
      const now = Date.now();
      const diff = (now - startTimeRef.current) / 1000;
      setElapsed(Math.min(10, diff));

      if (diff < 3.2) {
        setPhase(1);
      } else if (diff < 6.8) {
        setPhase(2);
      } else {
        setPhase(3);
      }

      if (diff >= 10) {
        clearInterval(interval);
        if (onComplete) onComplete();
      }
    }, 80);

    // Keyboard shortcut to skip (Escape or Space)
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' || e.key === ' ' || e.key === 'Enter') {
        e.preventDefault();
        clearInterval(interval);
        if (onComplete) onComplete();
      }
    };
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      clearInterval(interval);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [onComplete]);

  const handleSkip = () => {
    if (onComplete) onComplete();
  };

  const progressPercent = Math.min(100, (elapsed / 10) * 100);
  const secondsRemaining = Math.max(0, Math.ceil(10 - elapsed));

  return (
    <div
      role="region"
      aria-label="Bharat Masala Brand Experience"
      className="fixed inset-0 z-50 flex flex-col justify-between bg-[#140E0A] text-white overflow-hidden select-none"
    >
      {/* Ambient Saffron & Spice Ember Glows */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-32 -left-32 w-96 h-96 rounded-full bg-saffron-600/20 blur-3xl animate-pulse" />
        <div className="absolute top-1/2 -right-32 w-96 h-96 rounded-full bg-amber-600/15 blur-3xl animate-pulse" style={{ animationDelay: '1.5s' }} />
        <div className="absolute -bottom-32 left-1/3 w-96 h-96 rounded-full bg-cardamom-800/20 blur-3xl animate-pulse" style={{ animationDelay: '3s' }} />
        
        {/* Subtle decorative grid/grain */}
        <div className="absolute inset-0 bg-[radial-gradient(#D97706_1px,transparent_1px)] [background-size:32px_32px] opacity-[0.07]" />
      </div>

      {/* Top Header Controls: Brand Badge & Skip Button */}
      <header className="relative z-10 flex items-center justify-between px-6 py-6 sm:px-10">
        <div className="flex items-center gap-2 text-xs font-semibold text-saffron-300/80 tracking-widest uppercase">
          <span className="h-2 w-2 rounded-full bg-saffron-500 animate-ping" />
          <span>Western Ghats Harvest Heritage</span>
        </div>

        <button
          type="button"
          onClick={handleSkip}
          className="group flex items-center gap-2 rounded-full border border-saffron-500/30 bg-black/40 backdrop-blur-md px-4 py-2 text-xs font-semibold text-saffron-200 hover:bg-saffron-600 hover:text-white hover:border-saffron-500 transition-all shadow-lg"
          aria-label="Skip to store authentication"
        >
          <span>Skip to Store</span>
          <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
        </button>
      </header>

      {/* Center Stage: 3 Progressive Phases */}
      <main className="relative z-10 max-w-4xl mx-auto px-6 text-center my-auto flex flex-col items-center">
        {/* PHASE 1: Terroir & Mountain Origins (0s - 3.2s) */}
        {phase === 1 && (
          <div className="animate-fadeIn space-y-6">
            <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-950/60 px-4 py-1.5 text-xs font-semibold text-amber-300 shadow-inner">
              <Mountain className="h-4 w-4 text-amber-400" />
              <span>Thirthahalli &amp; Wayanad Canopy</span>
            </div>

            <h1 className="text-3xl sm:text-5xl md:text-6xl font-extrabold font-display tracking-tight text-transparent bg-clip-text bg-gradient-to-b from-amber-100 via-amber-200 to-amber-500 leading-tight">
              Where Rain-Fed Mist &amp; Ancient Soil<br />Nurture Pure Indian Spices
            </h1>

            <p className="max-w-xl mx-auto text-sm sm:text-base text-stone-300 font-light leading-relaxed">
              Harvested by multi-generational family growers under the evergreen canopies of Karnataka and Kerala.
            </p>
          </div>
        )}

        {/* PHASE 2: Brand Crest & Royal Heritage (3.2s - 6.8s) */}
        {phase === 2 && (
          <div className="animate-fadeIn space-y-6">
            {/* Grand Emblem Medallion */}
            <div className="mx-auto flex h-20 w-20 sm:h-24 sm:w-24 items-center justify-center rounded-3xl bg-gradient-to-br from-saffron-500 via-saffron-600 to-amber-900 text-white shadow-saffron-glow border border-amber-400/40 transform hover:scale-105 transition-transform">
              <span className="font-serif text-4xl sm:text-5xl font-bold tracking-wider text-amber-50">
                B
              </span>
            </div>

            <div className="space-y-2">
              <span className="text-xs sm:text-sm font-semibold tracking-[0.3em] uppercase text-saffron-400">
                Est. 1998 • Single-Origin Spices
              </span>
              <h1 className="text-4xl sm:text-6xl md:text-7xl font-bold font-display tracking-tight text-white drop-shadow-sm">
                BHARAT <span className="font-normal italic text-saffron-400">MASALA</span>
              </h1>
              <p className="text-sm sm:text-lg text-amber-100/90 font-display italic">
                “Pure Heritage Spices, Milled at Source”
              </p>
            </div>
          </div>
        )}

        {/* PHASE 3: The 4 Pillars of Uncompromising Purity (6.8s - 10s) */}
        {phase === 3 && (
          <div className="animate-fadeIn space-y-8">
            <div className="space-y-2">
              <span className="text-xs font-bold tracking-[0.25em] uppercase text-saffron-400">
                The Estate Guarantee
              </span>
              <h2 className="text-2xl sm:text-4xl font-bold font-display text-amber-100">
                Four Pillars of Farm-Fresh Purity
              </h2>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 max-w-3xl mx-auto">
              <div className="rounded-2xl border border-amber-500/20 bg-black/40 backdrop-blur-sm p-3.5 text-center">
                <div className="h-8 w-8 mx-auto rounded-lg bg-saffron-500/20 text-saffron-300 flex items-center justify-center mb-2">
                  <Mountain className="h-4 w-4" />
                </div>
                <h3 className="text-xs font-bold text-white mb-0.5">Single-Origin</h3>
                <p className="text-[11px] text-stone-400 leading-tight">Western Ghats Terroir</p>
              </div>

              <div className="rounded-2xl border border-amber-500/20 bg-black/40 backdrop-blur-sm p-3.5 text-center">
                <div className="h-8 w-8 mx-auto rounded-lg bg-saffron-500/20 text-saffron-300 flex items-center justify-center mb-2">
                  <Sun className="h-4 w-4" />
                </div>
                <h3 className="text-xs font-bold text-white mb-0.5">Sun-Dried</h3>
                <p className="text-[11px] text-stone-400 leading-tight">Courtyard Ripened</p>
              </div>

              <div className="rounded-2xl border border-amber-500/20 bg-black/40 backdrop-blur-sm p-3.5 text-center">
                <div className="h-8 w-8 mx-auto rounded-lg bg-saffron-500/20 text-saffron-300 flex items-center justify-center mb-2">
                  <Sparkles className="h-4 w-4" />
                </div>
                <h3 className="text-xs font-bold text-white mb-0.5">Cold-Ground</h3>
                <p className="text-[11px] text-stone-400 leading-tight">Aroma &amp; Oil Preserved</p>
              </div>

              <div className="rounded-2xl border border-amber-500/20 bg-black/40 backdrop-blur-sm p-3.5 text-center">
                <div className="h-8 w-8 mx-auto rounded-lg bg-saffron-500/20 text-saffron-300 flex items-center justify-center mb-2">
                  <ShieldCheck className="h-4 w-4" />
                </div>
                <h3 className="text-xs font-bold text-white mb-0.5">100% Pure</h3>
                <p className="text-[11px] text-stone-400 leading-tight">Zero Starch or Colors</p>
              </div>
            </div>

            <button
              type="button"
              onClick={handleSkip}
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-saffron-600 to-amber-600 px-6 py-3 text-xs font-bold tracking-wider uppercase text-white shadow-saffron-glow hover:brightness-110 transition-all"
            >
              <span>Enter Store &amp; Sign In</span>
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        )}
      </main>

      {/* Bottom Footer: Progress Bar & Countdown */}
      <footer className="relative z-10 px-6 py-6 sm:px-10 border-t border-white/10 bg-black/30 backdrop-blur-md">
        <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-xs text-stone-400">
            <Clock className="h-3.5 w-3.5 text-saffron-400" />
            <span>
              Opening storefront in <strong className="text-amber-200 font-mono">{secondsRemaining}s</strong> or press <kbd className="px-1.5 py-0.5 rounded bg-white/10 text-white font-mono text-[10px]">Esc</kbd>
            </span>
          </div>

          <div className="w-full sm:w-72 h-1.5 rounded-full bg-white/10 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-saffron-500 via-amber-400 to-saffron-300 transition-all duration-100 ease-linear rounded-full"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      </footer>
    </div>
  );
}
