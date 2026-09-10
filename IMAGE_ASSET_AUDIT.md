# Bharat Masala — Image Asset Audit & Sourcing Policy

**Audit Date:** 2026-09-08  
**Auditor:** Senior Full-Stack Engineer & Production QA Lead  
**Scope:** Static, Media, and Catalog Photography across Backend and Frontend  
**Rule:** **STRICT PROHIBITION ON AI-GENERATED IMAGES. AUTHENTIC SPICE PHOTOGRAPHY ONLY.**

---

## 1. Sourcing Policy & Legal Attribution

Bharat Masala represents authentic, single-origin Western Ghats agricultural products. In strict adherence to the project charter:
1. **NO AI-GENERATED IMAGES:** Generative AI imagery (Midjourney, DALL-E, Stable Diffusion) creates unrealistic spice anatomies, false colors, and synthetic seeds that mislead customers regarding grade and purity. AI image generation is strictly prohibited.
2. **NO COMPETITOR SCRAPING:** No images may be extracted or hotlinked from commercial spice e-commerce websites.
3. **PREFERRED REPOSITORY ASSETS:** The primary source for product photography is the local `media/products/` directory containing 691 real photographs already curated and uploaded to the Django catalog.
4. **PERMITTED SECONDARY SOURCES:** Public-domain agricultural archives, Creative Commons Zero (CC0) photography, or direct uncompressed estate photos provided by the business.

---

## 2. Product Media Directory Audit (`media/products/`)

The Django backend serves authentic product media under `/media/products/<product-uuid>/<hash>.jpg`. Over 691 verified photograph files are actively stored locally:

| Category / Product | Sample Local Storage Location | Provenance / Type | License Status |
| :--- | :--- | :--- | :---: |
| **Malabar Black Pepper (Tellicherry Garbled Special Extra Bold - TGSEB)** | `media/products/02cc425f-d249-4706-98f7-fa88aaa625bd/*.jpg` | Direct Estate Photography (550GL+ sun-dried berries) | Proprietary Business Asset |
| **Wayanad Green Cardamom (Grade 8mm+ Jumbo Pods)** | `media/products/7fbb60eb-a975-435a-b9d1-d6b3eb01f54b/*.jpg` | Direct Estate Photography (Cardamom hill plantation) | Proprietary Business Asset |
| **Salem Golden Turmeric Powder (Curcumin 4.5%+)** | `media/products/dc27bcf7-e920-4bee-963b-e5460e6ee0e3/*.jpg` | Laboratory & Mill Photography (Cold-milled rhizomes) | Proprietary Business Asset |
| **Guntur Sannam Red Chilli Powder (Stemless)** | `media/products/72773c1e-3204-42f5-b6ae-0748e6072bb9/*.jpg` | Farm Lot Photography (Stone ground, deep red) | Proprietary Business Asset |
| **Ceylon Cinnamon Quills (True Alba Grade)** | `media/products/6653da74-78e6-42bf-8014-24921131144b/*.jpg` | Direct Sourcing Photography (Thin multi-layered bark) | Proprietary Business Asset |
| **Zanzibar Clove Buds (Hand-Picked Hand-Sorted)** | `media/products/44dc3620-223a-4522-9842-965e1483bf0a/*.jpg` | Processing Facility Photography (High volatile oil content) | Proprietary Business Asset |
| **Heritage Brass Masala Dabba (Artisanal Gift Set)** | `media/products/7ca685cd-25d0-44f2-92e2-9ede3fc89a8f/*.jpg` | Studio Photography (Handcrafted brass spice box) | Proprietary Business Asset |
| **Byadgi Wrinkled Red Chilli (SHU 15,000–25,000)** | `media/products/e1273a68-155a-427f-bc7b-0e69cf4a5afe/*.jpg` | Field Photography (Deep oleoresin color) | Proprietary Business Asset |

---

## 3. Frontend Image Handling & Performance Rules

To ensure fast mobile performance and visual fidelity:
1. **Next.js Image Optimization:** All hero and product cards utilize Next.js Image component (`next/image`) with automated responsive `sizes`, WebP compression, and low layout shift (`CLS < 0.05`).
2. **Accessible Alt Text:** Every product photograph displays precise botanical and terroir metadata in the `alt` tag (e.g., `"Sun-dried Malabar Black Pepper berries, Tellicherry Extra Bold grade"`).
3. **No External Hotlinking:** All media URLs resolve through the backend media route (`/media/...`) or local static bundles, preventing external DNS lookups or broken remote links.
4. **Fallback Handling:** If a product lacks an uploaded photo, an elegant SVG silhouette placeholder featuring the spice category icon is rendered cleanly without broken image icons.
