# Bharat Masala - Production Deployment Guide
**Document Version:** 1.0.0  
**Target Environment:** Production (Linux / Docker / Cloud VM / Kubernetes)  
**Author:** Senior Full-Stack Engineer & Production QA Lead  

---

## 1. System Architecture Overview

```
                           [ Cloudflare / TLS Edge ]
                                      |
                                      v
                             [ Nginx Reverse Proxy ]
                            /                       \
           (Path: /api/*, /admin/*, /media/*)        (Path: /*)
                          |                               |
                          v                               v
             [ Django DRF Backend ]               [ Next.js 14 SSR ]
             Gunicorn (Port 8000)                 Node.js (Port 3000)
                 |            \
                 v             v
       [ PostgreSQL 16 ]    [ Redis 7 ]
                               |
                               v
                       [ Celery Workers ]
                    (Invoicing & Notifications)
```

---

## 2. Frontend Production Deployment (Next.js 14.2.35)

### 2.1 Environment Configuration (`.env.production`)
Create `frontend/.env.production` (never commit secret keys to Git):

```bash
# Public API Base URL for Browser Clients
NEXT_PUBLIC_API_BASE_URL=https://api.bharatmasala.com

# Standard API Prefix
NEXT_PUBLIC_API_PREFIX=/api/v1

# Internal Server-Side Backend URL for Next.js SSR / API Rewrites
BACKEND_INTERNAL_URL=http://127.0.0.1:8000

# Public Brand / Store Metadata
NEXT_PUBLIC_SITE_NAME=Bharat Masala
NEXT_PUBLIC_SUPPORT_WHATSAPP=+919876543210

# Razorpay Client Public Key (Public - Safe for browser)
NEXT_PUBLIC_RAZORPAY_KEY_ID=rzp_live_YourProductionKeyHere
```

### 2.2 Production Build & Verification
Run the production build:

```bash
cd frontend
npm ci --production=false
npm run build
```
Verify build output passes with **0 compilation errors** and all static/dynamic routes are successfully generated.

### 2.3 Process Management (PM2)
To keep the Next.js server running in production:

```bash
# Install PM2 globally if not installed
npm install -g pm2

# Start Next.js with PM2 cluster mode
pm2 start npm --name "bharat-frontend" -- start -- -p 3000
pm2 save
pm2 startup
```

---

## 3. Backend Production Deployment (Django 5 & DRF)

### 3.1 Python Environment & Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn psycopg2-binary
```

### 3.2 Production Environment Variables (`.env`)
Create `.env` at backend root:

```bash
# Django Core
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_SECRET_KEY=generate-a-strong-random-50-character-secret-key-here
DEBUG=False
DJANGO_ALLOWED_HOSTS=api.bharatmasala.com,bharatmasala.com,127.0.0.1

# PostgreSQL Database
DATABASE_URL=postgresql://bmp_user:YourStrongPassword@localhost:5432/bharat_masala_db

# Redis Cache & Broker
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# CORS & CSRF
CORS_ALLOWED_ORIGINS=https://bharatmasala.com,https://www.bharatmasala.com
CSRF_TRUSTED_ORIGINS=https://bharatmasala.com,https://www.bharatmasala.com,https://api.bharatmasala.com

# Razorpay Production Keys
RAZORPAY_KEY_ID=rzp_live_YourProductionKeyHere
RAZORPAY_KEY_SECRET=YourProductionSecretHere
RAZORPAY_WEBHOOK_SECRET=YourProductionWebhookSecretHere

# Security Headers
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
```

### 3.3 Database Migrations & Static Files
```bash
python manage.py migrate --settings=config.settings.production
python manage.py collectstatic --no-input --settings=config.settings.production
```

### 3.4 Gunicorn WSGI Server Execution
Run Gunicorn with appropriate worker calculation (`(2 * CPU_CORES) + 1`):

```bash
gunicorn config.wsgi:application \
    --name bharat_masala_api \
    --workers 4 \
    --worker-class gthread \
    --threads 2 \
    --worker-connections 1000 \
    --bind 127.0.0.1:8000 \
    --access-logfile /var/log/gunicorn/access.log \
    --error-logfile /var/log/gunicorn/error.log \
    --capture-output
```

### 3.5 Celery Worker & Beat (Background Tasks)
```bash
# Start Celery Worker for invoicing & notifications
celery -A config worker -l info --concurrency=4 -n worker1@%h

# Start Celery Beat for periodic tasks (stock reservation expiry cleanup)
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

---

## 4. Payment Gateway (Razorpay) Production Setup

1. **Merchant KYC**: Ensure Razorpay account is activated and KYC approved for live settlements.
2. **Key Generation**: Generate live API Keys from Razorpay Dashboard (`Settings > API Keys`).
3. **Configure Frontend**: Set `NEXT_PUBLIC_RAZORPAY_KEY_ID=rzp_live_...` in `frontend/.env.production`.
4. **Configure Backend**: Set `RAZORPAY_KEY_ID=rzp_live_...` and `RAZORPAY_KEY_SECRET=...` in backend `.env`.
5. **Configure Webhooks**:
   - URL: `https://api.bharatmasala.com/api/v1/payments/webhooks/razorpay/`
   - Secret: Match `RAZORPAY_WEBHOOK_SECRET` in backend `.env`.
   - Events:
     - `payment.captured`
     - `payment.failed`
     - `refund.processed`
     - `order.paid`

---

## 5. Nginx Reverse Proxy Configuration

```nginx
# /etc/nginx/sites-available/bharatmasala.conf

upstream frontend_upstream {
    server 127.0.0.1:3000;
    keepalive 32;
}

upstream backend_upstream {
    server 127.0.0.1:8000;
    keepalive 32;
}

server {
    listen 80;
    server_name bharatmasala.com www.bharatmasala.com api.bharatmasala.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name bharatmasala.com www.bharatmasala.com;

    ssl_certificate /etc/letsencrypt/live/bharatmasala.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bharatmasala.com/privkey.pem;

    # Frontend Next.js app
    location / {
        proxy_pass http://frontend_upstream;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # API endpoints routed to Django backend
    location /api/ {
        proxy_pass http://backend_upstream;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Django Admin
    location /admin/ {
        proxy_pass http://backend_upstream;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files served directly
    location /static/ {
        alias /var/www/bharatmasala/static/;
        expires 30d;
        add_header Cache-Control "public, max-age=2592000, immutable";
    }

    # Media files (Product estate photography)
    location /media/ {
        alias /var/www/bharatmasala/media/;
        expires 30d;
        add_header Cache-Control "public, max-age=2592000";
    }
}
```

---

## 6. Pre-Launch Verification Checklist

- [ ] `DEBUG=False` confirmed in production settings.
- [ ] Unique, high-entropy `DJANGO_SECRET_KEY` set.
- [ ] PostgreSQL connection pool validated.
- [ ] Redis and Celery worker running without errors.
- [ ] Razorpay Live Key ID and Secret configured in environment variables.
- [ ] SSL certificates active with A+ SSL Labs rating.
- [ ] All 25 Next.js routes compile (`npm run build`).
- [ ] 0 broken internal links verified via crawler.
- [ ] Media folder permissions readable by Nginx/Gunicorn.
- [ ] CORS and CSRF trusted origins restricted strictly to store domains.
- [ ] Backup cron configured for PostgreSQL database dumps.
