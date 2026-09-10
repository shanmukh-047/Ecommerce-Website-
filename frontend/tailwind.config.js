/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,jsx}',
    './components/**/*.{js,jsx}',
    './src/**/*.{js,jsx}',
  ],
  theme: {
    extend: {
      colors: {
        // --- Core Bharat Masala Brand Tokens ---
        // Saffron & Turmeric (Primary Brand Accent & CTA)
        saffron: {
          50: '#FFFBEB',
          100: '#FEF3C7',
          200: '#FDE68A',
          300: '#FCD34D',
          400: '#FBBF24',
          500: '#F59E0B',
          600: '#D97706', // Primary Brand Action
          700: '#B45309', // Hover state
          800: '#92400E',
          900: '#78350F',
          950: '#451A03',
          DEFAULT: '#D97706',
        },
        // Cardamom & Herbal Plantation (Secondary Terroir Accent)
        cardamom: {
          50: '#F0FDF4',
          100: '#DCFCE7',
          200: '#BBF7D0',
          300: '#86EFAC',
          400: '#4ADE80',
          500: '#22C55E',
          600: '#16A34A',
          700: '#15803D', // Secondary Accent
          800: '#166534', // Deep Organic Mark
          900: '#14532D',
          DEFAULT: '#15803D',
        },
        // Spice Earth & Stone (Deep Neutrals & Typography)
        spice: {
          earth: '#161311',    // Deep Charcoal / Espresso / Dark banner
          black: '#1C1917',    // Primary Body Text (Stone 900)
          charcoal: '#292524', // Stone 800
          stone: '#57534E',    // Secondary Text (Stone 600)
          muted: '#8C857B',    // Helper / Placeholder Text
          border: '#E7E2D9',   // Default Card & Divider Border
          borderSubtle: '#F0ECE3', // Subtle Separator
          canvas: '#FAF8F5',   // Warm Parchment Page Background
          surface: '#FFFFFF',  // Clean Pure White Surface
          elevated: '#F4EFEA', // Slightly Tinted Card/Dropdown
        },
        // Status & Semantic Feedback
        feedback: {
          success: '#16A34A',
          successBg: '#DCFCE7',
          warning: '#D97706',
          warningBg: '#FEF3C7',
          error: '#DC2626',
          errorBg: '#FEE2E2',
          info: '#0284C7',
          infoBg: '#E0F2FE',
        },
        // Backward-compatibility aliases for legacy components
        ink: '#FAF8F5',        // page background (warm parchment)
        charcoal: '#F4EFEA',   // alt section background
        charcoal2: '#FFFFFF',  // card surfaces
        gold: '#D97706',       // primary action saffron
        goldSoft: '#F59E0B',   // lighter saffron hover
        ember: '#EA580C',      // warm chili ember
        cream: '#1C1917',      // primary text
      },
      fontFamily: {
        display: ['var(--font-playfair)', 'Playfair Display', 'Georgia', 'serif'],
        body: ['var(--font-poppins)', 'Poppins', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
      },
      boxShadow: {
        'subtle': '0 1px 3px rgba(28, 25, 23, 0.05), 0 1px 2px rgba(28, 25, 23, 0.03)',
        'card': '0 2px 8px -1px rgba(28, 25, 23, 0.06), 0 1px 4px -1px rgba(28, 25, 23, 0.04)',
        'card-hover': '0 12px 24px -4px rgba(28, 25, 23, 0.10), 0 4px 10px -2px rgba(28, 25, 23, 0.04)',
        'drawer': '-4px 0 24px rgba(28, 25, 23, 0.15)',
        'modal': '0 20px 40px -8px rgba(28, 25, 23, 0.25)',
        'saffron-glow': '0 4px 16px -2px rgba(217, 119, 6, 0.35)',
        'goldGlow': '0 0 0 1px rgba(217, 119, 6, 0.22), 0 8px 30px rgba(217, 119, 6, 0.15)',
      },
      keyframes: {
        shimmer: {
          '100%': { transform: 'translateX(100%)' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(16px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideLeft: {
          '0%': { transform: 'translateX(100%)' },
          '100%': { transform: 'translateX(0)' },
        },
      },
      animation: {
        shimmer: 'shimmer 1.5s infinite',
        fadeIn: 'fadeIn 0.2s ease-out',
        slideUp: 'slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
        slideLeft: 'slideLeft 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
      },
    },
  },
  plugins: [],
};
