# Bharat Masala — Ecommerce Administration System Setup & Operations Guide

**Official Administration & Store Management Guide**  
**Version:** 1.0 (Production Release)  
**Applicable For:** Store Administrators, Fulfillment Managers, Customer Support Leads

---

## 1. Role-Based Access Hierarchy

The administration system utilizes Django's granular role and permission model to prevent unauthorized access to financial and catalog controls:

| Role | `is_staff` | `is_superuser` | Permitted Actions |
| :--- | :---: | :---: | :--- |
| **Super Administrator** | `True` | `True` | Full access across all domains, database management, staff account provisioning, gateway refunds, pricing rules. |
| **Store Manager** | `True` | `False` | Catalog management, pricing adjustments, payment verification, payment refunds, wholesale buyer approval. |
| **Operations Staff** | `True` | `False` | Daily order status updates, payment verification/rejection, stock level adjustments, image asset uploads. |
| **Customer / Wholesale** | `False` | `False` | Customer storefront only. Attempting to access `/admin-*` or `/admin/*` routes results in immediate redirection or 403 Forbidden. |

---

## 2. Provisioning Staff & Admin Accounts

### 2.1 Method A: Create Superuser via Terminal CLI
Run the standard Django superuser creation command in the backend root directory:
```bash
python manage.py createsuperuser --settings=config.settings.development
```
Follow the interactive prompts to set:
- **Email**: `admin@bharatmasala.com`
- **Phone Number**: `+919876543210`
- **First / Last Name**: `Admin User`
- **Password**: Set a strong passphrase (minimum 8 characters).

### 2.2 Method B: Promote an Existing User via Django Shell
If a staff member has already created an account via the customer registration screen, promote them using the interactive Django shell:
```bash
python manage.py shell --settings=config.settings.development
```
```python
from apps.accounts.models import User, Role

user = User.objects.get(email="staff.member@bharatmasala.com")
user.is_staff = True
user.role = Role.STAFF   # or Role.MANAGER
user.save()

print(f"User {user.email} promoted to staff: is_staff={user.is_staff}, role={user.role}")
```

### 2.3 Method C: One-Time Bootstrap for Production (Render Free Tier)
Because Render Free tier disables the interactive Web Shell, a dedicated, secure one-time bootstrap management command is built into the deployment pipeline (`build.sh`). It only executes when explicitly unlocked.

#### Step 1: Configure Environment Variables in Render Dashboard
Navigate to **Render Dashboard** &rarr; **`bharath-masala-api`** &rarr; **Environment**:
Add the following variables:
| Key | Value | Description |
| :--- | :--- | :--- |
| `BOOTSTRAP_ADMIN` | `true` | **Execution Gate**: Must be exactly `true`. Default is locked. |
| `ADMIN_EMAIL` | `admin@bharathmasala.com` | Target superuser email address. |
| `ADMIN_PASSWORD` | `YourComplexPassword123!` | Strong passphrase (minimum 8 characters, complex). |
| `ADMIN_PHONE` | `+919876543210` *(optional)* | Valid Indian mobile phone number (defaults to `+919876543210`). |

#### Step 2: Trigger a Deployment
1. Go to the **Deploy** dropdown in Render &rarr; Click **Clear build cache & deploy** (or push a commit).
2. During the build, `build.sh` automatically checks for `BOOTSTRAP_ADMIN=true` after applying database migrations and runs:
   ```bash
   python manage.py bootstrap_admin --settings=config.settings.production
   ```
3. The build log will confirm:
   ```text
   ==> BHARATH MASALA: ADMIN BOOTSTRAP COMPLETE
   ==> Status:      Created new Super Administrator account
   ==> Account:     admin@bharathmasala.com
   ==> Role:        Super Administrator
   ==> Flags:       is_staff=True, is_superuser=True, is_active=True
   ```
   *(Note: The plaintext password is never logged or printed).*

#### Step 3: Verify Admin Login
Log in immediately using your new credentials at:
- Frontend Proxy: `https://ecommerce-website-pearl-pi.vercel.app/admin/` or `https://bharathmasala.com/admin/`
- Direct Backend: `https://bharath-masala-api.onrender.com/admin/`

#### Step 4: CRITICAL — Remove Credentials from Render
Immediately after successful login:
1. Return to **Render Dashboard** &rarr; **`bharath-masala-api`** &rarr; **Environment**.
2. **DELETE** the `ADMIN_PASSWORD` environment variable.
3. Set `BOOTSTRAP_ADMIN=false` (or **DELETE** it).
4. Save changes. Subsequent builds will skip the bootstrap step and the command will refuse execution if invoked.

---

## 3. Accessing the Administration Portal

1. Open your browser and navigate to:
   - **Local Development**: `http://localhost:3000/admin-login`
   - **Production**: `https://bharatmasala.com/admin-login`
2. Enter your staff email address and password.
3. Upon authentication:
   - The platform verifies `user.is_staff === true` or `user.is_superuser === true`.
   - The user is automatically redirected to the **Store Operations Dashboard** at `/admin-dashboard`.
   - Non-staff users are blocked and displayed an access-denied screen.

---

## 4. Operational Standard Operating Procedures (SOPs)

### SOP 1: Verifying Manual UPI Payments
- **Location**: `/admin/payments`
- **Trigger**: New customer orders with UPI QR selection will display in the `Pending Verification` queue and increment the notification badge.
- **Procedure**:
  1. Click on **Payment Verifications** in the sidebar.
  2. Inspect the record: note the **Order Number**, **Payable Amount (₹)**, and the **12-digit Customer UTR**.
  3. If a screenshot was uploaded, click **View Receipt** to inspect the customer's payment screen.
  4. Open the business PhonePe App or Axis Bank statement. Match the credit:
     - Verify the exact amount received.
     - Confirm the UTR number in the bank transaction narration.
  5. **To Confirm**: Click **Verify** &rarr; Enter optional internal audit note &rarr; Click **Confirm & Capture**.
     - *Result*: Payment transitions to `CAPTURED`. Order automatically transitions to `CONFIRMED`.
  6. **To Reject**: If no funds arrived after 30 minutes, click **Reject** &rarr; Enter rejection reason (e.g., "UTR not matched in statement") &rarr; Click **Reject Payment**.
     - *Result*: Payment transitions to `FAILED`. Customer is prompted to retry.

### SOP 2: Managing Products & Catalog
- **Location**: `/admin/products`
- **Procedure**:
  - **Searching/Filtering**: Search by spice name or SKU; filter by category.
  - **Adding a New Spice**:
    1. Click **Add New Spice**.
    2. Enter Name, Category, Form (Whole / Cold-Milled / Blend), Tier (Reserve / Prime / Daily), HSN Code (`0910`), Packaging size (g), MRP, Selling Price, and Initial Stock.
    3. Click **Save Product & Allocate Stock**.
    4. *Result*: Master product, primary variant, and warehouse stock record are atomically created.
  - **Uploading Photography**:
    1. Click the **Upload Photo** icon on any product row.
    2. Choose a high-resolution estate JPEG/PNG and submit.

### SOP 3: Order Fulfillment & Courier Dispatch
- **Location**: `/admin/orders`
- **Procedure**:
  1. Filter by order status (e.g., `Confirmed`).
  2. Click **Manage** on the target order to open the fulfillment drawer.
  3. Review customer delivery address, contact phone, and ordered spices.
  4. Advance order status through the finite state machine:
     - `CONFIRMED` &rarr; Click **Transition to PROCESSING** (when batch is sent for cold-milling and packing).
     - `PROCESSING` &rarr; Click **Transition to SHIPPED** (when courier picks up package from Shimoga facility).
     - `SHIPPED` &rarr; Click **Transition to DELIVERED** (when carrier confirms delivery).

### SOP 4: Real-time Warehouse Inventory Management
- **Location**: `/admin/inventory`
- **Procedure**:
  1. View live stock balances across all product variants.
  2. Check the **Show Low Stock Only** checkbox to prioritize SKUs needing replenishment.
  3. To adjust physical inventory, click **Adjust** on any row:
     - Enter the new **Quantity on Hand**. (Note: the system enforces that `Quantity on Hand` must always be greater than or equal to active customer reservations).
     - Update the **Reorder Warning Threshold**.
     - Click **Save Stock Balance**.

---

## 5. Security & Session Best Practices

- **Staff Logout**: Always click the log out button in the sidebar footer before leaving a shared workstation.
- **Token Invalidation**: When a staff member logs out, their refresh token is blacklisted on the backend.
- **Session Duration**: Access tokens expire in 60 minutes; refresh tokens rotate automatically in the background without interrupting work.
