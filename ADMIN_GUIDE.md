# Bharat Masala — Store Operations & Administration Guide

**Document:** `ADMIN_GUIDE.md`  
**Date:** September 8, 2026  
**System:** Bharat Masala Enterprise Administration Panel  
**Audience:** Operations Managers, Store Administrators, Fulfillment Clerks, and Financial Auditors  

---

## 1. Access & Authentication

### 1.1 Routes
- **Staff / Admin Login Route:** `/admin-login` (or `/login` with staff/admin credentials)
- **Primary Operations Dashboard:** `/admin-dashboard`
- **Django Low-Level ORM Administration:** `/django-admin/` (Requires `Role.SUPERADMIN`)

### 1.2 Access Permissions
Access to admin surfaces is guarded by role-based access control (RBAC):
- `Role.STAFF`: Can view orders, update fulfillment statuses, confirm COD collections, view inventory, and review customer submissions.
- `Role.ADMIN` & `Role.SUPERADMIN`: Full administrative capabilities including editing product pricing, publishing/archiving SKUs, modifying stock inventory, processing refunds, and auditing system logs.

### 1.3 Superuser Credentials (Development / Staging)
- **Username / Email:** `admin@bharatmasala.com`
- **Password:** `AdminPassword123!`
- **Role:** Superadmin (`is_staff=True`, `is_superuser=True`)

---

## 2. Operations Dashboard (`/admin-dashboard`)

The dashboard provides real-time visibility into vital business operations:
1. **Financial KPIs:**
   - **Captured Revenue:** Real-time sum of all verified and collected payments across Razorpay, verified COD, and legacy UPI. (Mock data completely eliminated; computed directly from database records).
   - **Total Orders:** Aggregated count of all lifetime consumer and wholesale orders.
   - **To Fulfill:** Orders marked `CONFIRMED` or `PROCESSING` requiring picking, packing, or dispatch.
   - **Pending COD:** Count and value of outstanding Cash on Delivery shipments awaiting doorstep cash collection.
   - **Low Stock SKUs:** Alert badge listing catalog variants with available inventory falling below safe reorder thresholds (`safety_stock`).
2. **Quick Navigation Matrix:** Direct one-click access to Orders, Products, Payments, and Inventory.
3. **Recent Payments Feed:** Live chronological table showing transaction ID, customer email, amount, gateway (`Razorpay`, `Cash on Delivery`, `Manual UPI`), and live settlement status.

---

## 3. Product Catalog Management (`/admin/products`)

Store managers use this module to maintain product information, photography, and variant pricing:
- **Catalog Navigation:** Filter by Category (`Single Origin`, `Signature Blends`, `Whole Spices`), Search by name, SKU, or botanical terroir.
- **Product Photography:**
  - Every active product displays its authentic high-resolution hero image.
  - Image files reside in `media/products/<product_id>/` and are served with Next.js image optimization and caching.
- **Product Creation & Editing:**
  - Create new products with rich descriptions, tasting notes, harvest season, origin estate, and organic certifications.
  - Manage variants (e.g. 50g, 100g, 250g, 500g, 1kg) with specific packaging weights, MRP, selling price, and SKU barcodes.
  - Toggle publication visibility (`is_active=True/False`) to temporarily pause sales without deleting historical data.

---

## 4. Order Management & Fulfillment (`/admin/orders`)

- **Order Listing:**
  - Real-time search by Order Reference (e.g. `BMP-20260908-XXXXX`), customer name, or email.
  - Filter tabs by Order State: `All`, `Pending`, `Confirmed`, `Processing`, `Shipped`, `Delivered`, `Cancelled`.
  - Filter tabs by Payment Status: `All`, `Paid / Captured`, `Pending COD / Unpaid`, `Failed`.
- **Payment Method Badge:** Each order row clearly indicates payment method:
  - `Pay Online (Razorpay)` — Green badge when paid, orange when initiated.
  - `Cash on Delivery (COD)` — Indigo badge indicating payment collection required on delivery.
- **Fulfillment Workflow:**
  1. Orders placed via Razorpay arrive as `CONFIRMED` once payment signature is verified.
  2. Orders placed via COD arrive as `CONFIRMED` with payment status `PENDING`.
  3. Warehouse staff transition state to `PROCESSING` while packing.
  4. Once dispatched with courier, staff attach courier AWB tracking number and mark order `SHIPPED`.
  5. Automatic customer email, SMS, and WhatsApp dispatch notifications are triggered via the notification pipeline.

---

## 5. Payment Auditing & Settlement (`/admin/payments`)

The dedicated Payments Console provides financial oversight across all transaction types:
- **Filter Tabs by Gateway:**
  - `All Gateways`: Complete financial transaction ledger.
  - `Razorpay Online`: Transactions processed via Razorpay cards, UPI intent, and netbanking.
  - `Cash on Delivery`: Cash/UPI collected by logistics agents at doorstep.
  - `Legacy UPI QR`: Historical pre-migration transactions.
- **Filter Tabs by Status:**
  - `All`, `Captured`, `Pending`, `Failed`, `Refunded`.
- **Transaction Details Modal:**
  - View full metadata: Gateway Order ID (`order_xxx`), Gateway Payment ID (`pay_xxx`), customer billing address, and exact settlement timestamps.
  - Historical orders include the "View Customer Proof" modal to inspect legacy screenshot uploads and UTR numbers.

---

## 6. Cash on Delivery (COD) Management & Doorstep Reconciliation

### 6.1 Step-by-Step Collection Process
1. Delivery courier arrives at the customer's shipping address with the packaged order.
2. Courier hands over the package and collects the total order amount in physical cash or via courier UPI QR scan.
3. Logistics administrator navigates to `/admin/payments` and selects the **Cash on Delivery** filter tab.
4. Locate the specific order by Order Reference or Customer Name (status will display `PENDING`).
5. Click the green button: **"Mark Collected"**.
6. A confirmation modal will appear:
   > *"Confirm that payment of ₹... has been collected for Order #...?"*
7. Click **"Confirm Collection"**.
8. The system executes `POST /api/v1/staff/payments/{id}/mark-cod-collected/`:
   - Payment status transitions from `PENDING` $\rightarrow$ `CAPTURED`.
   - Order `payment_status` updates to `PAID`.
   - Notes are recorded with the staff member's email and timestamp.
   - Total captured revenue KPIs update in real-time on the main operations dashboard.

---

## 7. Inventory & Stock Control (`/admin/inventory`)

- **Stock Tracking:** Real-time visibility into `physical_stock`, `allocated_stock` (reserved for pending checkouts), and `available_stock`.
- **Safety Stock Thresholds:** Automatically highlights variants reaching critically low thresholds to avoid overselling.
- **Stock Restocking:** Direct bulk adjustments allowing warehouse teams to log inward purchase orders, batch numbers, and production lot expiry dates.
