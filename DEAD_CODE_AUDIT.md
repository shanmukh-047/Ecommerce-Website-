# Bharat Masala — Dead Code & Prototype Audit Report

**Audit Date:** 2026-09-08  
**Auditor:** Senior Full-Stack Engineer & Production QA Lead  
**Scope:** Frontend Codebase (`frontend/`) and Residual Prototype Files  
**Objective:** Identify and Safely Quarantine Unused Prototype Code without Breaking Active Routes

---

## 1. Inventory of Potential Dead Code

During the evolution of the project from an initial UI prototype to the production Bharat Masala single-origin spice e-commerce platform, several early prototype files remained in the repository.

Each candidate file was audited by checking all import statements across `frontend/app/`, `frontend/components/`, `frontend/context/`, `frontend/hooks/`, and `frontend/services/`:

| File Path | Description / Contents | Imported in Active App? | Recommendation |
| :--- | :--- | :---: | :--- |
| `frontend/data/menu.json` | 824 lines of Chinese restaurant items ("Veg Fried Rice", "Steamed Momos", "Schezwan Noodles") | **NO** | Confirmed Dead Code. Safe to archive or remove. |
| `frontend/data/menuHelpers.js` | Helper functions filtering `menu.json` categories | **NO** | Confirmed Dead Code. Safe to archive or remove. |
| `frontend/components/Menu.jsx` | Restaurant food menu view referencing `menu.json` | **NO** | Confirmed Dead Code. Safe to archive or remove. |
| `frontend/components/Reservation.jsx` | Restaurant dining table reservation form | **NO** | Confirmed Dead Code. Safe to archive or remove. |
| `frontend/components/SpecialDishes.jsx` | Restaurant chef specials (Crispy Chilli Babycorn, Momos) | **NO** | Confirmed Dead Code. Safe to archive or remove. |
| `frontend/components/Offers.jsx` | Restaurant food combo offers ("Buy 2 Get 1 Fried Rice") | **NO** | Confirmed Dead Code. Safe to archive or remove. |
| `frontend/components/Contact.jsx` (root) | Prototype contact form | **NO** (Not imported; Footer has direct links) | Confirmed Dead Code. Replace with dedicated `app/contact/page.js`. |
| `frontend/components/Gallery.jsx` | Restaurant dining hall photography | **NO** | Confirmed Dead Code. Safe to archive or remove. |
| `frontend/components/CartDrawer.jsx` (root) | Early prototype cart drawer referencing `menuHelpers.js` | **NO** (Active drawer is `components/cart/CartDrawer.jsx`) | Confirmed Dead Code. Safe to archive or remove. |
| `frontend/components/Navbar.jsx` (root) | Early prototype navbar referencing `#reservation`, `#home` | **NO** (Active header is `components/layout/Header.jsx`) | Confirmed Dead Code. Safe to archive or remove. |
| `frontend/components/About.jsx` (root) | Early prototype about section with restaurant wok story | **NO** (Active storytelling is `components/home/Storytelling.jsx`) | Confirmed Dead Code. Safe to archive or remove. |

---

## 2. Confirmation of Zero Impact on Production Build

An automated import dependency trace confirmed that:
1. `frontend/app/layout.js` only imports `components/layout/Header.jsx`, `components/layout/Footer.jsx`, and `components/layout/Providers.jsx`.
2. `frontend/components/layout/Providers.jsx` only imports `components/cart/CartDrawer.jsx` (the production cart drawer).
3. `frontend/app/page.js` only imports components from `components/home/*`.
4. None of the listed legacy prototype files are bundled into the production output of `npm run build`.

---

## 3. Quarantining & Deletion Plan

In Phase 21, these 11 confirmed dead files will be safely moved to an archive or removed to maintain clean, production-grade repository hygiene.
