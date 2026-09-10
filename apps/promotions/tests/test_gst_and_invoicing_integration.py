from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Address, User
from apps.cart.services import CartService
from apps.catalog.models import Category, Form, Product, ProductVariant, Tier
from apps.inventory.services import InventoryService
from apps.invoices.services.invoice_service import InvoiceService
from apps.orders.services.checkout_service import CheckoutService, OrderStateMachine
from apps.promotions.models import Coupon, DiscountType


class GSTAndInvoicingIntegrationTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.user = User.objects.create_user(
            "gst_shopper@example.com", "9876543261", "StrongPassword123!"
        )
        self.address = Address.objects.create(
            user=self.user,
            recipient_name="Deepa Rao",
            phone_number="9876543261",
            address_line_1="123 Malenadu Way",
            city="Thirthahalli",
            state="KARNATAKA",
            pincode="577432",
        )

        self.category = Category.objects.create(name="Spices", slug="spices-gst")
        self.product1 = Product.objects.create(
            name="Sirsi Pepper",
            slug="sirsi-pepper-gst",
            category=self.category,
            tier=Tier.EVERYDAY,
            form=Form.WHOLE,
            hsn_code="09041110",
            gst_rate=Decimal("5.00"),
        )
        self.variant1 = ProductVariant.objects.create(
            product=self.product1,
            variant_name="500g",
            sku="BMP-PEPPER-GST-1",
            weight_in_grams=500,
            mrp=Decimal("500.00"),
            selling_price=Decimal("400.00"),
        )
        InventoryService.add_stock(self.variant1, 50)

        self.product2 = Product.objects.create(
            name="Kumta Cardamom",
            slug="kumta-cardamom-gst",
            category=self.category,
            tier=Tier.EVERYDAY,
            form=Form.WHOLE,
            hsn_code="09083100",
            gst_rate=Decimal("5.00"),
        )

        self.variant2 = ProductVariant.objects.create(
            product=self.product2,
            variant_name="100g",
            sku="BMP-CARDAMOM-GST-2",
            weight_in_grams=100,
            mrp=Decimal("350.00"),
            selling_price=Decimal("300.00"),
        )
        InventoryService.add_stock(self.variant2, 50)

        self.coupon = Coupon.objects.create(
            code="SPICE100",
            discount_type=DiscountType.FIXED_AMOUNT,
            discount_value=Decimal("100.00"),
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=7),
        )

    def test_discount_invoicing_hamilton_hare_exactness(self):
        cart = CartService.get_or_create_user_cart(self.user)
        CartService.add_item(cart, self.variant1, 2)  # 2 x 400 = 800
        CartService.add_item(cart, self.variant2, 1)  # 1 x 300 = 300
        # Subtotal: 1100.00
        # Discount: 100.00
        # Grand total: 1000.00
        cart.applied_coupon = self.coupon
        cart.save()

        order = CheckoutService.create_order_from_cart(self.user, self.address.id)
        self.assertEqual(order.items_subtotal, Decimal("1100.00"))
        self.assertEqual(order.total_discount, Decimal("100.00"))
        self.assertEqual(order.grand_total, Decimal("1000.00"))

        # Transition to CONFIRMED
        OrderStateMachine.transition_status(order, "CONFIRMED", actor=self.user)

        # Generate Invoice
        invoice = InvoiceService.generate_invoice(order)

        # Verify invoice totals
        self.assertEqual(invoice.items_subtotal, Decimal("1100.00"))
        self.assertEqual(invoice.total_discount, Decimal("100.00"))
        self.assertEqual(invoice.grand_total, Decimal("1000.00"))

        # Verify line items discount sum equals total_discount without 1-paisa drift
        invoice_lines = list(invoice.lines.all())
        total_line_discounts = sum(line.discount_amount for line in invoice_lines)
        self.assertEqual(total_line_discounts, Decimal("100.00"))

        # Check that sum of net totals equals 1000.00
        total_net = sum(line.total_amount for line in invoice_lines)
        self.assertEqual(total_net, Decimal("1000.00"))

        # Section 15(3) CGST Act check:
        # Each line's tax is calculated on (gross - discount), NOT on gross!
        for line in invoice_lines:
            expected_taxable = (line.total_amount / Decimal("1.05")).quantize(Decimal("0.01"))
            self.assertEqual(line.taxable_amount, expected_taxable)
            self.assertEqual(
                line.total_amount, (line.unit_price * line.quantity) - line.discount_amount
            )
