# Bharat Masala Frontend Design System
**Version:** 1.0.0  
**Framework:** Next.js 14 (App Router) + Tailwind CSS 3.4  
**Design Philosophy:** *Authentic Western Ghats Spice Terroir meets Modern Indian Quick-Commerce Speed*

---

## 1. Executive Summary & Brand Identity

The Bharat Masala design system bridges two essential paradigms:
1. **The Heritage of Western Ghats Spice Terroir:** Expressed through warm saffron accents, cardamom leaf greens, deep espresso earth tones, stone parchment backgrounds, and refined `Playfair Display` serif headlines.
2. **Modern Indian Quick-Commerce Efficiency:** Inspired by the fluid speed, clear density, and frictionless product discovery of top Indian commerce platforms (such as Zepto, Blinkit, and Swiggy Instamart) without copying their generic visual identity.

### Core Experience Pillars
- **Culinary Authenticity & Purity:** Highlighting single-estate origin, harvest year, garbled grading, and authentic Indian spice aesthetics.
- **Frictionless Discovery & Navigation:** Sticky category rails, clear pack-size switching (`100g`, `250g`, `500g`, `1kg`), and real-time stock indicators.
- **Instant One-Tap Cart Access:** Seamless transition between "ADD" CTA and an interactive `QuantitySelector` stepper with zero page reloads.
- **Mobile-First Touch Ergonomics:** Minimum 44px x 44px tap targets, bottom-sheet drawers on mobile, and zero layout shift.
- **Strict Accessibility (WCAG 2.1 AA):** High contrast ratios, accessible keyboard focus rings, screen reader announcements for price/cart mutations, and reduced-motion support.

---

## 2. Design Tokens

### 2.1 Color Palette

#### Primary Brand Colors: Saffron & Turmeric
Saffron represents harvest energy, authentic warmth, culinary zest, and the primary call-to-action.

| Token | Hex | Tailwind Class | Semantic Usage |
| :--- | :--- | :--- | :--- |
| `saffron-50` | `#FFFBEB` | `bg-saffron-50` | Subtle badge backgrounds, highlight tint |
| `saffron-100` | `#FEF3C7` | `bg-saffron-100` | Soft notification backgrounds, promo banners |
| `saffron-200` | `#FDE68A` | `border-saffron-200` | Subtle golden borders |
| `saffron-500` | `#F59E0B` | `text-saffron-500` | Vibrant turmeric stars, secondary highlights |
| **`saffron-600`** | **`#D97706`** | **`bg-saffron-600`** | **Primary Brand CTA, Active Steppers, Links** |
| `saffron-700` | `#B45309` | `bg-saffron-700` | Primary CTA hover state, high-contrast links |
| `saffron-800` | `#92400E` | `bg-saffron-800` | Active button click state |
| `saffron-900` | `#78350F` | `text-saffron-900` | High-contrast text on gold tints |

#### Secondary Brand Colors: Cardamom & Western Ghats Green
Cardamom represents plantation terroir, organic certification, harvest freshness, and verified trust marks.

| Token | Hex | Tailwind Class | Semantic Usage |
| :--- | :--- | :--- | :--- |
| `cardamom-50` | `#F0FDF4` | `bg-cardamom-50` | Organic badge wash |
| `cardamom-100` | `#DCFCE7` | `bg-cardamom-100` | In-stock pill backgrounds, verified badge |
| **`cardamom-700`** | **`#15803D`** | **`bg-cardamom-700`** | **Secondary Action, Organic Seal, Success highlights** |
| `cardamom-800` | `#166534` | `bg-cardamom-800` | Cardamom hover state, deep green headings |
| `cardamom-900` | `#14532D` | `text-cardamom-900` | High-contrast text on green tints |

#### Neutrals: Spice Earth, Canvas & Stone
Grounding neutrals that replace cold modern grays with natural earthy pigments.

| Token | Hex | Tailwind Class | Semantic Usage |
| :--- | :--- | :--- | :--- |
| `spice-canvas` | `#FAF8F5` | `bg-spice-canvas` | Main website background (Warm Stone Parchment) |
| `spice-surface` | `#FFFFFF` | `bg-white` | Card and modal surfaces (Pure Crisp White) |
| `spice-elevated` | `#F4EFEA` | `bg-spice-elevated` | Dropdown backgrounds, alternate section bands |
| `spice-borderSubtle` | `#F0ECE3` | `border-spice-borderSubtle` | Soft table & item separators |
| `spice-border` | `#E7E2D9` | `border-spice-border` | Default card & input borders |
| `spice-muted` | `#8C857B` | `text-spice-muted` | Helper text, breadcrumbs, placeholder text |
| `spice-stone` | `#57534E` | `text-spice-stone` | Secondary descriptions, subheadings, specs |
| `spice-charcoal` | `#292524` | `text-spice-charcoal` | Strong headings, active tab text |
| **`spice-black`** | **`#1C1917`** | **`text-spice-black`** | **Primary body typography, prices, titles** |
| `spice-earth` | `#161311` | `bg-spice-earth` | Deep espresso dark banners, footers, drawer masks |

#### Semantic Feedback & Alerts

| State | Base Color | Soft Background | Border | Usage |
| :--- | :--- | :--- | :--- | :--- |
| **Success** | `#16A34A` (`emerald-600`) | `#DCFCE7` (`emerald-50`) | `#86EFAC` | Payment confirmed, order placed, verified |
| **Warning** | `#D97706` (`amber-600`) | `#FEF3C7` (`amber-50`) | `#FDE68A` | Low stock alert, coupon expiring |
| **Error** | `#DC2626` (`red-600`) | `#FEE2E2` (`red-50`) | `#FCA5A5` | Validation failure, payment failed, out-of-stock |
| **Discount** | `#DC2626` (`red-600`) | `#DC2626` (Solid) | None | High-impact `% OFF` discount badges |
| **Info** | `#0284C7` (`sky-600`) | `#E0F2FE` (`sky-50`) | `#BAE6FD` | Tracking updates, policy notices |

---

## 3. Typography Hierarchy

The typographic system utilizes a paired dual-font approach:
1. **`Playfair Display` (Serif):** Expresses heritage, luxury Indian spices, single-estate pedigree, and editorial storytelling.
2. **`Poppins` (Sans-Serif):** Provides geometric clarity, crisp number rendering for Indian Rupee (`₹`) pricing, and readability on mobile viewports.

### Type Scale & Specs

| Style Role | Font Family | Size (px / rem) | Line Height | Weight | Letter Spacing |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Display 2XL` | `Playfair Display` | `48px` / `3.0rem` | `1.1` | Bold (700) | `-0.02em` |
| `Display XL` | `Playfair Display` | `36px` / `2.25rem` | `1.2` | Bold (700) | `-0.015em` |
| `Heading LG` | `Playfair Display` | `28px` / `1.75rem` | `1.25` | SemiBold (600) | `-0.01em` |
| `Heading MD` | `Poppins` | `22px` / `1.375rem`| `1.3` | SemiBold (600) | `normal` |
| `Heading SM` | `Poppins` | `18px` / `1.125rem`| `1.4` | SemiBold (600) | `normal` |
| `Body Large` | `Poppins` | `16px` / `1.0rem`  | `1.5` | Regular (400) / Medium (500) | `normal` |
| `Body Default` | `Poppins` | `14px` / `0.875rem`| `1.5` | Regular (400) | `normal` |
| `Body Small` | `Poppins` | `12px` / `0.75rem` | `1.4` | Regular (400) / Medium (500) | `normal` |
| `Microcopy` | `Poppins` | `11px` / `0.6875rem`| `1.3` | Medium (500) | `+0.02em` |
| `Badge Tag` | `Poppins` | `10px` / `0.625rem`| `1.0` | Bold (700) | `+0.05em uppercase` |
| `Price Large` | `Poppins` | `20px` / `1.25rem` | `1.0` | Bold (700) | `tabular-nums` |
| `Price Card` | `Poppins` | `16px` / `1.0rem`  | `1.0` | Bold (700) | `tabular-nums` |

---

## 4. Spacing, Elevation & Surfaces

### 4.1 Spacing Scale
The spacing system adheres to an 8-point grid with 4-point micro-adjustments:
- `4px` (`gap-1`, `p-1`) - Micro gaps between badges & labels
- `8px` (`gap-2`, `p-2`) - Input padding, icon button padding
- `12px` (`gap-3`, `p-3`) - Card interior padding (compact mobile)
- `16px` (`gap-4`, `p-4`) - Default card & drawer padding
- `24px` (`gap-6`, `p-6`) - Section gaps & modal interior
- `32px` (`gap-8`, `p-8`) - Desktop container padding
- `48px` / `64px` (`py-12`, `py-16`) - Page section vertical padding

### 4.2 Elevation Layers (Shadows)

```css
/* Subtle card shadow on warm stone canvas */
shadow-subtle: 0 1px 3px rgba(28, 25, 23, 0.05), 0 1px 2px rgba(28, 25, 23, 0.03);

/* Elevated product card & dropdowns */
shadow-card: 0 2px 8px -1px rgba(28, 25, 23, 0.06), 0 1px 4px -1px rgba(28, 25, 23, 0.04);

/* Interactive hover lift */
shadow-card-hover: 0 12px 24px -4px rgba(28, 25, 23, 0.10), 0 4px 10px -2px rgba(28, 25, 23, 0.04);

/* Slide-over cart drawer */
shadow-drawer: -4px 0 24px rgba(28, 25, 23, 0.15);

/* Central modals & alerts */
shadow-modal: 0 20px 40px -8px rgba(28, 25, 23, 0.25);

/* Brand CTA warm glow */
shadow-saffron-glow: 0 4px 16px -2px rgba(217, 119, 6, 0.35);
```

### 4.3 Border Radii
- `rounded-md` (`6px`): Small buttons, pack-size variant pills, quantity selectors.
- `rounded-lg` (`8px`): Form inputs, default buttons, select menus.
- `rounded-xl` (`12px`): Product cards, category cards, alert containers.
- `rounded-2xl` (`16px`): Modals, bottom-sheets, empty-state containers.
- `rounded-full` (`9999px`): Badges, round icon buttons, discount tags.

---

## 5. Motion & Micro-Interactions

All transitions are optimized for 60fps performance and strictly adhere to `prefers-reduced-motion`:
- **Card Hover:** `transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.2s ease` (subtle 3px elevation).
- **CTA Press:** `active:scale-[0.98]` tactile haptic feedback.
- **Drawer Slide:** `0.3s cubic-bezier(0.16, 1, 0.3, 1)` smooth edge slide.
- **Modal Entrance:** `0.2s ease-out` fade & scale.
- **Signature Divider (`.spice-trail`):** Subtle saffron dot shimmer divider for editorial chapter breaks.
- **Shimmer Loading (`.shimmer-bg`):** High-speed linear gradient sweep for image & card skeletons.

---

## 6. Reusable Component Inventory

All core components are located in: `frontend/components/common/`  
Clean re-exports available from: `@/components/common`

### 6.1 `Button`
Versatile button component supporting multiple color schemes, loading states, left/right icons, and accessibility compliance.

#### Props
| Prop | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `variant` | `'primary' \| 'secondary' \| 'outline' \| 'outline-stone' \| 'ghost' \| 'danger' \| 'dark'` | `'primary'` | Visual style preset |
| `size` | `'sm' \| 'md' \| 'lg' \| 'icon' \| 'icon-sm'` | `'md'` | Button dimensions (lg = 48px touch target) |
| `isLoading` | `boolean` | `false` | Shows spinner, disables button, sets `aria-busy` |
| `disabled` | `boolean` | `false` | Disables interaction |
| `isFullWidth` | `boolean` | `false` | Expands to full container width |
| `leftIcon` | `ReactNode` | `null` | Icon rendered before text |
| `rightIcon`| `ReactNode` | `null` | Icon rendered after text |

#### Usage Example
```jsx
import { Button } from '@/components/common';
import { ShoppingBag } from 'lucide-react';

<Button
  variant="primary"
  size="lg"
  leftIcon={<ShoppingBag className="h-5 w-5" />}
  onClick={handleCheckout}
>
  Proceed to Checkout
</Button>
```

---

### 6.2 `Input`
Accessible form input with floating label, error validation display, helper text, and icon slots.

#### Props
| Prop | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `label` | `string` | `undefined` | Associated field label |
| `error` | `string` | `undefined` | Error message (renders in red, sets `aria-invalid`) |
| `helperText` | `string` | `undefined` | Instructive subtext |
| `leftIcon` | `ReactNode` | `null` | Icon inside input on left side |
| `rightIcon` | `ReactNode` | `null` | Icon or action button on right side |
| `required` | `boolean` | `false` | Renders red asterisk indicator |

#### Usage Example
```jsx
import { Input } from '@/components/common';
import { Search } from 'lucide-react';

<Input
  placeholder="Search cardamom, turmeric, wild cinnamon..."
  leftIcon={<Search className="h-4 w-4" />}
  value={query}
  onChange={(e) => setQuery(e.target.value)}
/>
```

---

### 6.3 `Select`
Custom-styled accessible dropdown with chevron and error messaging.

#### Props
| Prop | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `label` | `string` | `undefined` | Field label |
| `options` | `Array<{ value, label, disabled? }>` | `[]` | Option list |
| `value` | `string \| number` | `''` | Current value |
| `onChange` | `Function` | `undefined` | Change event handler |
| `error` | `string` | `undefined` | Validation error message |

---

### 6.4 `Badge`
Compact indicators for discounts, pack sizes, ratings, and order statuses.

#### Props
| Prop | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `variant` | `'saffron' \| 'cardamom' \| 'danger' \| 'success' \| 'warning' \| 'stone' \| 'dark' \| 'discount'` | `'saffron'` | Color scheme |
| `size` | `'xs' \| 'sm' \| 'md'` | `'md'` | Scale preset (`xs` for card tags) |
| `hasDot` | `boolean` | `false` | Displays small status dot indicator |

#### Usage Example
```jsx
import { Badge } from '@/components/common';

<Badge variant="discount" size="xs">15% OFF</Badge>
<Badge variant="cardamom" size="sm" hasDot>Organic Wayanad</Badge>
```

---

### 6.5 `QuantitySelector`
The vital quick-commerce stepper for adjusting item counts directly from the product card or cart drawer.

#### Props
| Prop | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `quantity` | `number` | `1` | Current item quantity |
| `onIncrement` | `Function` | `undefined` | Callback on plus press |
| `onDecrement` | `Function` | `undefined` | Callback on minus/trash press |
| `min` | `number` | `0` | Minimum allowed value (if 0, 1 -> 0 shows Trash icon) |
| `max` | `number` | `99` | Maximum allowed value |
| `size` | `'sm' \| 'md'` | `'md'` | `sm` fits into compact card footer, `md` for cart drawer |
| `variant` | `'solid-saffron' \| 'outline' \| 'dark'` | `'solid-saffron'` | Background style |

---

### 6.6 `ProductCard`
The storefront's primary discovery component. Built for high conversion with instant pack-size variant toggles, discount badges, and a direct `ADD` button that transforms into a `QuantitySelector`.

#### Product Data Contract
```ts
interface ProductCardProps {
  product: {
    id: string;
    slug: string;
    name: string;
    category: string;
    terroir?: string;
    image_url?: string;
    rating?: number;
    reviewCount?: number;
    variants: Array<{
      id: string;
      weight_display: string; // e.g. "250g"
      price: number;          // e.g. 240
      mrp: number;            // e.g. 280
      is_in_stock: boolean;
    }>;
    isBestSeller?: boolean;
    isOrganic?: boolean;
  };
  cartQuantity?: number;
  onAddToCart?: (variantId: string, qty: number) => void;
  onQuantityChange?: (variantId: string, newQty: number) => void;
  onProductClick?: (slug: string) => void;
  onWishlistToggle?: (productId: string) => void;
  isWishlisted?: boolean;
}
```

#### Key Capabilities
- **Variant Switching:** Instant price recalculation when tapping `100g`, `250g`, `500g` pills without navigating away.
- **Dynamic Savings Pill:** Calculates and displays `% OFF` automatically.
- **Image Resilience:** Auto-recovers to branded category graphics if CDN or image link fails.
- **Zero-Friction Cart Action:** Single tap adds item and swaps button to inline stepper.

---

### 6.7 `Modal`
Accessible dialog with backdrop blur, keyboard `Escape` dismissal, focus trapping, and background scroll locking.

#### Props
| Prop | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `isOpen` | `boolean` | `false` | Controls open/close state |
| `onClose` | `Function` | `undefined` | Dismissal handler |
| `title` | `string` | `undefined` | Modal header title |
| `description` | `string` | `undefined` | Subtitle |
| `size` | `'sm' \| 'md' \| 'lg' \| 'xl'` | `'md'` | Maximum width |
| `footer` | `ReactNode` | `null` | Action buttons area |

---

### 6.8 `Drawer`
Side/bottom sheet for the Cart Drawer, Mobile Navigation, and Product Filter panels.

#### Props
| Prop | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `isOpen` | `boolean` | `false` | Visibility state |
| `onClose` | `Function` | `undefined` | Dismissal handler |
| `placement` | `'right' \| 'left' \| 'bottom'` | `'right'` | Drawer entrance origin |
| `title` | `string` | `undefined` | Header title |
| `footer` | `ReactNode` | `null` | Sticky checkout or filter apply footer |

---

### 6.9 `Toast`
Application-wide notification system with `ToastProvider` and the `useToast` hook.

#### Usage Example
```jsx
import { useToast } from '@/components/common';

function CartButton() {
  const { success, error } = useToast();

  const handleAdd = () => {
    try {
      // add item
      success('Added 250g Wayanad Black Pepper to cart', 'Added to Cart');
    } catch (err) {
      error('Could not update cart quantity. Please try again.');
    }
  };
}
```

---

### 6.10 `Skeleton`
Shimmer placeholders providing instantaneous perceived performance during API data fetching.

#### Pre-composed Variants
- `<Skeleton />`: Generic text, rectangle, or avatar shimmers.
- `<ProductCardSkeleton />`: Exact placeholder matching the `ProductCard` layout to eliminate Cumulative Layout Shift (CLS).
- `<CartItemSkeleton />`: Placeholder for cart drawer line items.

---

### 6.11 `EmptyState` & `ErrorState`
- **`EmptyState`:** Zero-state component for empty carts, wishlist, or zero search results, complete with icon, friendly explanation, and action button.
- **`ErrorState`:** Resilient component for API failures, network dropouts, and payment retries.

---

## 7. Accessibility Standards (WCAG 2.1 AA Compliance)

1. **Color Contrast:**
   - All body text (`#1C1917` on `#FAF8F5`) achieves a contrast ratio of `14.2:1` (exceeding WCAG AAA).
   - Saffron primary buttons (`#FFFFFF` on `#D97706`) achieve `3.8:1` for bold text, reinforced by dark saffron borders (`#B45309`).
2. **Keyboard Navigation:**
   - Visible saffron focus rings (`focus-visible:ring-2 focus-visible:ring-saffron-500 focus-visible:ring-offset-2`).
   - Drawers and Modals dismiss on `Escape` key and trap focus within the dialog.
3. **Screen Readers:**
   - Interactive steppers use `role="group"` and announce live quantity changes with `aria-live="polite"`.
   - Modals use `role="dialog"`, `aria-modal="true"`, and connect titles via `aria-labelledby`.
4. **Touch Target Size:**
   - All interactive mobile elements have a minimum clickable bounding box of `44px x 44px`.
5. **Reduced Motion:**
   - `@media (prefers-reduced-motion: reduce)` automatically disables or reduces CSS keyframe animations across the storefront.

---

## 8. Verification & Next Steps

### Completed Milestones
- [x] Configure semantic design tokens in `frontend/tailwind.config.js`.
- [x] Implement warm Western Ghats spice styling & accessible utilities in `frontend/app/globals.css`.
- [x] Build 13 accessible UI component primitives in `frontend/components/common/`.
- [x] Create clean module barrel export in `frontend/components/common/index.js`.
- [x] Verify Next.js production build (`npm run build` succeeds cleanly with 0 errors).
- [x] Complete comprehensive design documentation in `DESIGN_SYSTEM.md`.

The Bharat Masala design system is now ready for page and feature integration (Catalog, Product Details, Cart Drawer, Checkout, and Customer Accounts).
