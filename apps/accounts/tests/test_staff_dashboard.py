from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.catalog.models import Category, Product, ProductVariant
from apps.inventory.models import StockItem
from apps.orders.models import Order, OrderStatus
from apps.payments.models import Payment, PaymentGateway, PaymentMethod, PaymentStatus

User = get_user_model()


class StaffDashboardAndInventoryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff_client = APIClient()

        self.customer = User.objects.create_user(
            email="cust_dash@example.com",
            phone_number="9876500001",
            password="Password123!",
            role="CUSTOMER",
        )
        self.staff_user = User.objects.create_user(
            email="admin_dash@bharathmasala.com",
            phone_number="9876500002",
            password="AdminPassword123!",
            role="STAFF",
            is_staff=True,
        )

        self.client.force_authenticate(user=self.customer)
        self.staff_client.force_authenticate(user=self.staff_user)

        self.category = Category.objects.create(name="Blends", slug="blends")
        self.product = Product.objects.create(
            name="Sambar Masala",
            slug="sambar-masala",
            category=self.category,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_name="250g",
            sku="SAM-250G",
            weight_in_grams=250,
            mrp=Decimal("200.00"),
            selling_price=Decimal("180.00"),
        )
        self.stock_item = StockItem.objects.create(
            variant=self.variant,
            quantity_on_hand=5,
            reorder_level=10,  # low stock!
        )

        self.order = Order.objects.create(
            order_number="BMP-DASH-01",
            user=self.customer,
            order_status=OrderStatus.CONFIRMED,
            items_subtotal=Decimal("180.00"),
            shipping_fee=Decimal("50.00"),
            tax_amount=Decimal("9.00"),
            grand_total=Decimal("239.00"),
            total_quantity=1,
            total_weight_in_grams=250,
            shipping_recipient_name="Test Customer",
            shipping_phone_number="9876500001",
            shipping_address_line_1="Estate",
            shipping_city="Sirsi",
            shipping_state="KA",
            shipping_pincode="581401",
        )

        self.payment = Payment.objects.create(
            payment_number="PAY-DASH-01",
            order=self.order,
            user=self.customer,
            status=PaymentStatus.PENDING_VERIFICATION,
            gateway=PaymentGateway.PHONEPE_QR,
            payment_method=PaymentMethod.UPI,
            gateway_payment_id="998877665544",
            utr_number="998877665544",
            amount=Decimal("239.00"),
        )

    def test_customer_cannot_access_staff_dashboard(self):
        resp = self.client.get("/api/v1/staff/dashboard/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_can_fetch_dashboard_metrics(self):
        resp = self.staff_client.get("/api/v1/staff/dashboard/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        stats = resp.data["stats"]
        self.assertGreaterEqual(stats["total_orders"], 1)
        self.assertGreaterEqual(stats["pending_payments"], 1)
        self.assertGreaterEqual(stats["low_stock_products"], 1)
        self.assertEqual(len(resp.data["recent_orders"]), 1)
        self.assertEqual(len(resp.data["recent_payments"]), 1)

    def test_staff_can_list_and_update_inventory(self):
        # 1. List inventory
        list_resp = self.staff_client.get("/api/v1/staff/inventory/")
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(list_resp.data["count"], 1)

        # 2. Filter low stock
        low_resp = self.staff_client.get("/api/v1/staff/inventory/?low_stock=true")
        self.assertEqual(low_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(low_resp.data["count"], 1)

        # 3. Update stock item
        patch_resp = self.staff_client.patch(
            f"/api/v1/staff/inventory/{self.stock_item.id}/",
            {"quantity_on_hand": 50, "reorder_level": 15},
            format="json",
        )
        self.assertEqual(patch_resp.status_code, status.HTTP_200_OK)

        self.stock_item.refresh_from_db()
        self.assertEqual(self.stock_item.quantity_on_hand, 50)
        self.assertEqual(self.stock_item.reorder_level, 15)

    def test_staff_product_crud(self):
        # 1. Create product
        create_payload = {
            "name": "Organic Cardamom Whole",
            "category": str(self.category.id),
            "tier": "RESERVE",
            "form": "WHOLE",
            "short_description": "Green Malenadu cardamom pods",
            "variant_name": "50g Pack",
            "weight_in_grams": 50,
            "mrp": "250.00",
            "selling_price": "220.00",
            "initial_stock": 30,
        }
        create_resp = self.staff_client.post(
            "/api/v1/staff/catalog/products/",
            create_payload,
            format="json",
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        prod_id = create_resp.data["product"]["id"]

        # 2. Update product
        update_resp = self.staff_client.patch(
            f"/api/v1/staff/catalog/products/{prod_id}/",
            {"name": "Organic Cardamom Bold Reserve", "selling_price": "210.00", "stock": 45},
            format="json",
        )
        self.assertEqual(update_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(update_resp.data["product"]["name"], "Organic Cardamom Bold Reserve")

        # 3. Verify stock was updated
        prod = Product.objects.get(id=prod_id)
        var = prod.variants.first()
        self.assertEqual(var.stock_item.quantity_on_hand, 45)
