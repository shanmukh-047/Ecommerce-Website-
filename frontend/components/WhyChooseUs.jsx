'use client';
import { useReveal, SectionTag } from './Shared';

const POINTS = [
  { icon: '🌿', title: 'Fresh Ingredients' },
  { icon: '⚡', title: 'Fast Delivery' },
  { icon: '👨‍🍳', title: 'Experienced Chefs' },
  { icon: '💰', title: 'Affordable Pricing' },
  { icon: '🔥', title: 'Freshly Prepared' },
  { icon: '✅', title: 'Quality Checked' },
];

export default function WhyChooseUs() {
  useReveal();
  return (
    <section className="py-28 px-6 bg-charcoal">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-14 reveal">
          <SectionTag>Why Masala Box</SectionTag>
          <h2 className="font-display text-4xl md:text-5xl font-semibold">Why Choose Us</h2>
        </div>
        <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-6">
          {POINTS.map((p, i) => (
            <div
              key={i}
              className="reveal flex items-center gap-4 bg-charcoal2 border border-gold/10 rounded-2xl p-6 hover:border-gold/40 transition-colors shadow-sm"
              style={{ transitionDelay: `${i * 70}ms` }}
            >
              <span className="text-3xl">{p.icon}</span>
              <span className="font-display text-lg">{p.title}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
