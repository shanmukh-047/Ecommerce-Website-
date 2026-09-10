'use client';
import { useReveal, SectionTag } from './Shared';

const REVIEWS = [
  { name: 'Ananya R.', text: 'The butter garlic fried rice is unreal — best Indo-Chinese in the neighbourhood.', rating: 5 },
  { name: 'Karthik M.', text: 'Dragon momos have real heat and the delivery is always fast and hot.', rating: 5 },
  { name: 'Divya S.', text: 'Ordered the weekend combo for a family dinner, everyone had a favourite.', rating: 5 },
  { name: 'Rohit P.', text: 'Consistent quality every single time. The paneer butter masala is a must.', rating: 4 },
];

export default function Reviews() {
  useReveal();
  return (
    <section id="reviews" className="py-28 bg-charcoal overflow-hidden">
      <div className="max-w-7xl mx-auto px-6 text-center mb-14 reveal">
        <SectionTag>Customer Love</SectionTag>
        <h2 className="font-display text-4xl md:text-5xl font-semibold">What People Are Saying</h2>
      </div>
      <div className="relative">
        <div className="flex gap-6 marquee-track w-max px-6">
          {[...REVIEWS, ...REVIEWS].map((r, i) => (
            <div key={i} className="w-80 shrink-0 bg-charcoal2/90 border border-gold/15 rounded-2xl p-7 shadow-sm">
              <div className="text-gold mb-3">
                {'★'.repeat(r.rating)}
                {'☆'.repeat(5 - r.rating)}
              </div>
              <p className="text-cream/75 text-sm mb-5 leading-relaxed">&quot;{r.text}&quot;</p>
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-gradient-to-br from-gold to-ember flex items-center justify-center text-white text-xs font-bold">
                  {r.name.split(' ').map((w) => w[0]).join('')}
                </div>
                <p className="text-sm font-medium">{r.name}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
