# Bharat Masala — Broken Route & Link Audit Report

**Audit Date:** 2026-09-08  
**Scope:** Complete Navigation Crawl across Header, Footer, MobileNav, AccountMenu, and Homepage CTAs  
**Target:** 0 Customer-Facing Broken Routes (0 404 Errors)  
**Status:** **AUDITED — 11 MISSING ROUTES IDENTIFIED FOR IMPLEMENTATION**

---

## 1. Route Crawl Results

Every internal route referenced across the frontend code was crawled and categorized:

| # | Route / Link Target | Referenced In | HTTP Status Before Fix | Action Classification | Resolution Plan |
| :---: | :--- | :--- | :---: | :---: | :--- |
| 1 | `/` | Header, Footer, MobileNav | 200 OK | **WORKING** | Homepage active. |
| 2 | `/products` | Header, Footer, MobileNav, Buttons | 200 OK | **WORKING** | Product catalog active. |
| 3 | `/products/[slug]` | Product Cards, Catalog Grid | 200 OK | **WORKING** | Product detail active. |
| 4 | `/cart` | Header, Drawer, MobileNav | 200 OK | **WORKING** | Shopping cart active. |
| 5 | `/checkout` | Cart Drawer, Cart Page | 200 OK | **WORKING** | Checkout page active. |
| 6 | `/login` | Header, MobileNav, RouteGuard | 200 OK | **WORKING** | Login page active. |
| 7 | `/register` | Header, Login Page, HomeCTA | 200 OK | **WORKING** | Retail registration active. |
| 8 | `/account` | Header, MobileNav, AccountMenu | 200 OK | **WORKING** | Profile overview active. |
| 9 | `/account/orders` | Header, Footer, MobileNav | 200 OK | **WORKING** | Order history active. |
| 10 | `/account/orders/[id]` | Order Cards, Invoices | 200 OK | **WORKING** | Order details active. |
| 11 | `/track` | Header, Footer, Order Details | 200 OK | **WORKING** | Public AWB tracking active. |
| 12 | `/wholesale` | Header, Footer, MobileNav, AccountMenu | **404 NOT FOUND** | **MISSING ROUTE** | Create `frontend/app/wholesale/page.js` with B2B registration and benefits. |
| 13 | `/about` | Header, Navbar | **404 NOT FOUND** | **MISSING ROUTE** | Create `frontend/app/about/page.js` with Western Ghats terroir and heritage. |
| 14 | `/our-story` | Functional Brief | **404 NOT FOUND** | **MISSING ROUTE** | Create `frontend/app/our-story/page.js` as alias/redirect to `/about`. |
| 15 | `/offers` | Functional Brief | **404 NOT FOUND** | **MISSING ROUTE** | Create `frontend/app/offers/page.js` displaying active harvest coupons. |
| 16 | `/gifts` | Functional Brief | **404 NOT FOUND** | **MISSING ROUTE** | Create `frontend/app/gifts/page.js` displaying heritage spice boxes & hampers. |
| 17 | `/stories` | Functional Brief | **404 NOT FOUND** | **MISSING ROUTE** | Create `frontend/app/stories/page.js` with Sharada's oral folklore and recipe lore. |
| 18 | `/contact` | Footer, Trust Strip | **404 NOT FOUND** | **MISSING ROUTE** | Create `frontend/app/contact/page.js` with customer care and plantation address. |
| 19 | `/shipping-policy` | Footer | **404 NOT FOUND** | **MISSING ROUTE** | Create `frontend/app/shipping-policy/page.js` with courier SLAs and timelines. |
| 20 | `/returns` | Footer | **404 NOT FOUND** | **MISSING ROUTE** | Create `frontend/app/returns/page.js` with perishable food return policy and RMA guidance. |
| 21 | `/terms` | Footer | **404 NOT FOUND** | **MISSING ROUTE** | Create `frontend/app/terms/page.js` with GST terms and conditions of sale. |
| 22 | `/privacy` | Footer | **404 NOT FOUND** | **MISSING ROUTE** | Create `frontend/app/privacy/page.js` with customer data and PCI-DSS compliance policy. |
| 23 | `/account/addresses` | AccountMenu | **404 NOT FOUND** | **MISSING REDIRECT** | Create `frontend/app/account/addresses/page.js` that redirects to `/account#addresses`. |

---

## 2. Summary & Verification Criteria
- **Total Internal Routes Audited:** 23
- **Currently Passing (200 OK):** 11
- **Currently Failing (404 Not Found):** 12
- **Required Fixes:** 11 dedicated pages + 1 redirect route.
- **Verification Rule:** Following Phase 1 implementation, an automated route crawler must verify that 100% of internal links resolve with HTTP 200.
