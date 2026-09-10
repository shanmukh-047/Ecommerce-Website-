# Bharat Masala — Premium E-Commerce Frontend

Production-ready frontend for the **Bharat Masala** single-origin spice e-commerce platform. Built with **Next.js 14 (App Router)**, **React 18**, and **Tailwind CSS**, communicating with an authoritative **Django REST Framework** backend.

---

## 1. Setup & Installation

### Prerequisites
- **Node.js**: `v18.17.0` or higher (Node 20+ recommended)
- **npm**: `v9.0.0` or higher
- **Backend**: Django REST Framework backend running on `http://127.0.0.1:8000` (or your configured API host)

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Configure Environment Variables
Copy the provided `.env.example` template to create your local development configuration:
```bash
cp .env.example .env.local
```

Verify or adjust values in `.env.local`:
```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_API_PREFIX=/api/v1
BACKEND_INTERNAL_URL=http://127.0.0.1:8000
```

### 3. Run Development Server
```bash
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser to access the storefront.

---

## 2. Backend Connection (Development)

During local development, the frontend interacts with the Django backend running at:
```text
http://127.0.0.1:8000
```

### Connection Mechanism
The frontend connects through a dual-mode centralized client (`lib/apiClient.js`):

1. **Next.js Rewrite Proxy (Same-Origin Emulation):**
   - Configured in `next.config.js`:
     ```javascript
     async rewrites() {
       return [
         {
           source: '/api/v1/:path*',
           destination: `${process.env.BACKEND_INTERNAL_URL || 'http://127.0.0.1:8000'}/api/v1/:path*`,
         },
       ];
     }
     ```
   - In the browser, API calls to `/api/v1/...` are proxied directly to Django, eliminating cross-origin cookie blockers.

2. **Direct API Base URL:**
   - If `NEXT_PUBLIC_API_BASE_URL` is explicitly set (e.g. `http://127.0.0.1:8000`), the client resolves absolute URLs and automatically attaches `/api/v1` prefixes with zero redundant slashes.

3. **Authentication & Session Credentials:**
   - All fetch operations specify `credentials: 'include'`.
   - The client automatically stores the short-lived JWT `access_token` and injects `Authorization: Bearer <token>`.
   - The long-lived `refresh_token` and guest cart tokens are maintained in secure `HttpOnly` cookies.
   - On `HTTP 401 Unauthorized`, the client serializes concurrent requests and automatically calls `POST /api/v1/auth/token/refresh/` to renew tokens silently.

---

## 3. Production Configuration & Deployment

Frontend deployment is completely independent from backend hosting. The application can be deployed to **Vercel**, **Netlify**, **Cloudflare Pages**, **AWS Amplify**, or containerized with **Docker / Kubernetes**.

### 1. Production Environment Variables
Set the following environment variables in your production deployment dashboard (e.g. Vercel Project Settings or Docker `.env.production`):

| Variable | Description | Production Example |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_API_BASE_URL` | Publicly accessible domain of the Django API | `https://api.bharatmasala.com` |
| `NEXT_PUBLIC_API_PREFIX` | Standard API version prefix | `/api/v1` |
| `BACKEND_INTERNAL_URL` | *(Optional)* Internal network URL for SSR rewrites | `http://backend-service:8000` |
| `NEXT_PUBLIC_SITE_NAME` | Display site name | `Bharat Masala` |
| `NEXT_PUBLIC_SUPPORT_WHATSAPP` | Customer concierge WhatsApp number | `+919876543210` |

### 2. Backend CORS Requirements (Django)
For cross-domain production deployments (e.g., frontend on `https://bharatmasala.com` and backend on `https://api.bharatmasala.com`), the Django backend must be configured with `django-cors-headers`:

```python
# config/settings/production.py

CORS_ALLOWED_ORIGINS = [
    "https://bharatmasala.com",
    "https://www.bharatmasala.com",
]

# Mandatory for HttpOnly JWT refresh cookies and guest cart sessions:
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = [
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "OPTIONS",
]

CORS_ALLOW_HEADERS = [
    "accept",
    "authorization",
    "content-type",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-request-id",
]

# CSRF Trusted Origins for state-modifying requests
CSRF_TRUSTED_ORIGINS = [
    "https://bharatmasala.com",
    "https://www.bharatmasala.com",
]
```

---

## 4. Build & Verification Commands

### Build for Production
```bash
npm run build
```
The production build compiles optimized static and dynamic pages with zero lint errors and tree-shaken JavaScript bundles.

### Run Production Server
```bash
npm start
```
Starts the Next.js production Node server on port 3000.

### Code Linting
```bash
npm run lint
```

---

## 5. Architecture & Code Quality

```text
frontend/
├── app/                      # Next.js 14 App Router
│   ├── layout.js             # Root layout with fonts, metadata, Header & Footer
│   ├── page.js               # Dynamic homepage composing brand & catalog sections
│   ├── login/                # Authentication: Customer & Wholesale login
│   ├── register/             # Retail & B2B Wholesale registration
│   ├── products/             # Product catalog listing & search
│   │   └── [slug]/           # Product details with pack size variant selection
│   ├── cart/                 # Shopping cart with dynamic totals
│   ├── checkout/             # Address selection, order placement & Razorpay modal
│   ├── track/                # Public unauthenticated AWB shipment tracking
│   └── account/              # Customer profile, address book & order history
│       └── orders/[id]/      # Order confirmation, payment audit, & consignment tracking
│
├── components/
│   ├── home/                 # Dynamic Homepage sections (Hero, Categories, Featured, etc.)
│   ├── common/               # Design system primitives (Button, Input, Badge, ProductCard)
│   ├── layout/               # Header, Mobile Navigation, Footer, Providers
│   └── checkout/             # Razorpay payment modal with HMAC verification
│
├── context/
│   ├── AuthContext.jsx       # Global authentication state & user profile
│   └── CartContext.jsx       # Dynamic shopping cart state & stock validation
│
├── hooks/
│   └── useApi.js             # Standardized API lifecycle hook (Loading, Error, Empty, Abort)
│
├── lib/
│   └── apiClient.js          # Centralized fetch wrapper, interceptors & error normalizer
│
└── services/                 # Domain-specific backend API services
    ├── authService.js        # /api/v1/auth/
    ├── catalogService.js     # /api/v1/catalog/
    ├── cartService.js        # /api/v1/cart/
    ├── orderService.js       # /api/v1/orders/
    ├── paymentService.js     # /api/v1/payments/
    └── shippingService.js    # /api/v1/shipping/
```

### Production Checklist & Hardening
- **Zero Localhost Hardcoding:** URL resolution uses dynamic environment variables (`NEXT_PUBLIC_API_BASE_URL`) or relative paths (`''`).
- **Standard Envelope Normalization:** Automatically unpacks `{ success, request_id, message, data, error }`, attaching non-enumerable metadata.
- **Friendly User Errors:** `formatApiErrorMessage` shields end users from backend tracebacks, SQL details, or internal server paths.
- **Request Cancellation:** Built-in `AbortController` integration auto-cancels obsolete queries during tab switching and search typing.
- **Zero Leaked Secrets:** Frontend code is completely free of private API keys, payment gateway secret keys, or database credentials.
