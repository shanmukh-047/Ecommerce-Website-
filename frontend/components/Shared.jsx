'use client';
import { useEffect, useMemo } from 'react';

export function useReveal() {
  useEffect(() => {
    const els = document.querySelectorAll('.reveal');
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) e.target.classList.add('show');
        });
      },
      { threshold: 0.12 }
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  });
}

export function EmberField({ count = 16 }) {
  const embers = useMemo(
    () =>
      Array.from({ length: count }, () => ({
        left: Math.random() * 100,
        size: 3 + Math.random() * 5,
        dur: 8 + Math.random() * 10,
        delay: Math.random() * 10,
      })),
    [count]
  );
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {embers.map((e, i) => (
        <span
          key={i}
          className="particle"
          style={{
            left: `${e.left}%`,
            width: e.size,
            height: e.size,
            animationDuration: `${e.dur}s`,
            animationDelay: `${e.delay}s`,
          }}
        />
      ))}
      <span className="steam" style={{ left: '30%', animationDelay: '0s' }} />
      <span className="steam" style={{ left: '55%', animationDelay: '2.4s' }} />
      <span className="steam" style={{ left: '72%', animationDelay: '4.6s' }} />
    </div>
  );
}

export function SpiceTrail() {
  return <div className="spice-trail my-6 max-w-xs" />;
}

export function SectionTag({ children }) {
  return (
    <p className="tracking-[0.35em] text-xs font-semibold text-gold/90 uppercase mb-3">
      {children}
    </p>
  );
}
