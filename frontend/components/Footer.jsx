export default function Footer() {
  return (
    <footer className="bg-ink border-t border-gold/10 pt-16 pb-8 px-6">
      <div className="max-w-7xl mx-auto grid sm:grid-cols-2 md:grid-cols-4 gap-10 mb-12">
        <div>
          <p className="font-display text-2xl mb-3">
            MASALA <span className="text-gold">BOX</span>
          </p>
          <p className="text-cream/50 text-sm leading-relaxed">
            Authentic taste, modern experience — Indo-Chinese fusion done right.
          </p>
        </div>
        <div>
          <p className="text-gold text-sm tracking-widest uppercase mb-4">Quick Links</p>
          <ul className="space-y-2 text-sm text-cream/60">
            {['Home', 'Our Menu', 'Reservation', 'Contact'].map((l) => (
              <li key={l}>
                <a href={`#${l.toLowerCase().replace(/\s+/g, '-')}`} className="hover:text-gold transition-colors">
                  {l}
                </a>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="text-gold text-sm tracking-widest uppercase mb-4">Opening Hours</p>
          <p className="text-cream/60 text-sm">
            Mon – Sun
            <br />
            11:00 AM – 11:00 PM
          </p>
        </div>
        <div>
          <p className="text-gold text-sm tracking-widest uppercase mb-4">Newsletter</p>
          <div className="flex gap-2">
            <input
              placeholder="Your email"
              className="bg-charcoal2 border border-gold/20 rounded-full py-2 px-4 text-xs flex-1"
            />
            <button className="bg-gold text-white text-xs font-semibold px-4 rounded-full">Join</button>
          </div>
        </div>
      </div>
      <div className="max-w-7xl mx-auto border-t border-gold/10 pt-6 text-center text-xs text-cream/40">
        © {new Date().getFullYear()} Masala Box. All rights reserved. · Built for demo purposes.
      </div>
    </footer>
  );
}
