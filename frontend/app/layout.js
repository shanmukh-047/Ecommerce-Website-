import './globals.css';
import Providers from '../components/layout/Providers';
import Header from '../components/layout/Header';
import Footer from '../components/layout/Footer';
import StorefrontAccessGate from '../components/layout/StorefrontAccessGate';

export const metadata = {
  title: 'Bharat Masala — Authentic Western Ghats Single Origin Spices',
  description:
    'Hand-harvested, single-origin Malabar black pepper, Wayanad cardamom, Salem turmeric, and artisanal masalas directly from estate farmers.',
  keywords: 'spices, single origin, black pepper, cardamom, turmeric, cinnamon, cloves, Western Ghats, Bharat Masala',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="bg-spice-canvas text-spice-black antialiased font-body flex flex-col min-h-screen selection:bg-saffron-600 selection:text-white">
        <Providers>
          <StorefrontAccessGate>
            <Header />
            <main className="flex-1 w-full">{children}</main>
            <Footer />
          </StorefrontAccessGate>
        </Providers>
      </body>
    </html>
  );
}
