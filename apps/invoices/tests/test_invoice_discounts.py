"""
Comprehensive tests for statutory GST Invoice discount allocation,
replacement orders, and financial invariants (ISSUE-003).
"""

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import IndianStates, User
from apps.catalog.models import Category, Product, ProductVariant
from apps.invoices.services.invoice_service import InvoiceService
from apps.orders.models import Order, OrderLineItem, OrderStatus


class InvoiceDiscountAndGSTIntegrityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="discount_tester@bharathmasala.com",
            phone_number="+919876543003",
            first_name="GST",
            last_name="Tester",
        )
        self.category = Category.objects.create(name="Spices", slug="spices-disc")

        self.product1 = Product.objects.create(
            category=self.category,
            name="Rasam Powder",
            slug="rasam-disc",
            hsn_code="0904",
            gst_rate=Decimal("5.00"),
        )
        self.variant1 = ProductVariant.objects.create(
            product=self.product1,
            variant_name="500g",
            sku="RASAM-500G-DISC",
            weight_in_grams=500,
            mrp=Decimal("200.00"),
            selling_price=Decimal("200.00"),
        )

        self.product2 = Product.objects.create(
            category=self.category,
            name="Biryani Masala",
            slug="biryani-disc",
            hsn_code="0907",
            gst_rate=Decimal("12.00"),
        )
        self.variant2 = ProductVariant.objects.create(
            product=self.product2,
            variant_name="200g",
            sku="BIRYANI-200G-DISC",
            weight_in_grams=200,
            mrp=Decimal("300.00"),
            selling_price=Decimal("300.00"),
        )

    def _create_variant(self, name: str, sku: str, price: Decimal) -> ProductVariant:
        return ProductVariant.objects.create(
            product=self.product1,
            variant_name=name,
            sku=sku,
            weight_in_grams=100,
            mrp=price,
            selling_price=price,
        )

    def _create_order(
        self,
        items_subtotal: Decimal,
        total_discount: Decimal,
        shipping_fee: Decimal = Decimal("0.00"),
        state=IndianStates.KARNATAKA,
        is_b2b=False,
    ) -> Order:
        grand_total = max(Decimal("0.00"), items_subtotal - total_discount + shipping_fee)
        order = Order.objects.create(
            order_number=f"BMP-ORD-DISC-{timezone.now().timestamp()}",
            user=self.user,
            order_status=OrderStatus.CONFIRMED,
            items_subtotal=items_subtotal,
            total_discount=total_discount,
            shipping_fee=shipping_fee,
            tax_amount=Decimal("0.00"),
            grand_total=grand_total,
            currency="INR",
            total_quantity=2,
            is_wholesale_order=is_b2b,
            shipping_recipient_name="GST Discount Tester",
            shipping_phone_number="+919876543003",
            shipping_address_line_1="789 Tax Avenue",
            shipping_city="Bangalore",
            shipping_state=state,
            shipping_pincode="560001",
        )
        return order

    def test_1_no_discount_invoice_matches_standard_calculation(self):
        """1. Order with no discount produces exact statutory invoice without discount lines."""
        order = self._create_order(
            items_subtotal=Decimal("400.00"),
            total_discount=Decimal("0.00"),
            shipping_fee=Decimal("40.00"),
            state=IndianStates.KARNATAKA,
        )
        OrderLineItem.objects.create(
            order=order,
            variant=self.variant1,
            quantity=2,
            product_name="Rasam Powder",
            variant_name="500g",
            sku=self.variant1.sku,
            weight_in_grams=500,
            mrp=Decimal("200.00"),
            unit_price=Decimal("200.00"),
            line_subtotal=Decimal("400.00"),
        )

        invoice = InvoiceService.generate_invoice(order)

        self.assertEqual(invoice.items_subtotal, Decimal("400.00"))
        self.assertEqual(invoice.total_discount, Decimal("0.00"))
        self.assertEqual(invoice.grand_total, Decimal("440.00"))
        # 400.00 inclusive of 5% GST -> Taxable = 400 / 1.05 = 380.95, Tax = 19.05
        self.assertEqual(invoice.taxable_subtotal, Decimal("380.95"))
        self.assertEqual(invoice.cgst_amount, Decimal("9.53"))
        self.assertEqual(invoice.sgst_amount, Decimal("9.52"))
        self.assertEqual(invoice.total_tax, Decimal("19.05"))

        # Invariant: taxable + total_tax + shipping = grand_total
        self.assertEqual(
            invoice.taxable_subtotal + invoice.total_tax + invoice.shipping_fee,
            invoice.grand_total,
        )

    def test_2_percentage_coupon_discount_reduces_taxable_and_tax(self):
        """2. Percentage coupon discount reduces net taxable value and GST liability."""
        # 10% discount on 500.00 items = 50.00 discount -> Net 450.00
        order = self._create_order(
            items_subtotal=Decimal("500.00"),
            total_discount=Decimal("50.00"),
            state=IndianStates.KARNATAKA,
        )
        OrderLineItem.objects.create(
            order=order,
            variant=self.variant1,
            quantity=2,
            product_name="Rasam Powder",
            variant_name="500g",
            sku=self.variant1.sku,
            weight_in_grams=500,
            mrp=Decimal("250.00"),
            unit_price=Decimal("250.00"),
            line_subtotal=Decimal("500.00"),
        )

        invoice = InvoiceService.generate_invoice(order)

        self.assertEqual(invoice.items_subtotal, Decimal("500.00"))
        self.assertEqual(invoice.total_discount, Decimal("50.00"))
        self.assertEqual(invoice.grand_total, Decimal("450.00"))

        # Net line value = 450.00. Taxable = 450.00 / 1.05 = 428.57, Tax = 21.43
        self.assertEqual(invoice.taxable_subtotal, Decimal("428.57"))
        self.assertEqual(invoice.total_tax, Decimal("21.43"))

        # Invariant check
        self.assertEqual(
            invoice.taxable_subtotal + invoice.total_tax + invoice.shipping_fee,
            invoice.grand_total,
        )

    def test_3_fixed_amount_discount_deducted_consistently(self):
        """3. Fixed-amount discount is deducted from gross turnover prior to GST split."""
        order = self._create_order(
            items_subtotal=Decimal("600.00"),
            total_discount=Decimal("100.00"),
            shipping_fee=Decimal("50.00"),
            state=IndianStates.KARNATAKA,
        )
        OrderLineItem.objects.create(
            order=order,
            variant=self.variant2,
            quantity=2,
            product_name="Biryani Masala",
            variant_name="200g",
            sku=self.variant2.sku,
            weight_in_grams=200,
            mrp=Decimal("300.00"),
            unit_price=Decimal("300.00"),
            line_subtotal=Decimal("600.00"),
        )

        invoice = InvoiceService.generate_invoice(order)

        self.assertEqual(invoice.items_subtotal, Decimal("600.00"))
        self.assertEqual(invoice.total_discount, Decimal("100.00"))
        self.assertEqual(invoice.grand_total, Decimal("550.00"))  # 600 - 100 + 50

        # Net line total = 500.00 at 12% GST: Taxable = 500 / 1.12 = 446.43, Tax = 53.57
        self.assertEqual(invoice.taxable_subtotal, Decimal("446.43"))
        self.assertEqual(invoice.total_tax, Decimal("53.57"))
        self.assertEqual(invoice.cgst_amount + invoice.sgst_amount, Decimal("53.57"))

        # Invariant check
        self.assertEqual(
            invoice.taxable_subtotal + invoice.total_tax + invoice.shipping_fee,
            invoice.grand_total,
        )

    def test_4_multiple_items_proportional_discount_allocation(self):
        """4. Multiple items with different GST rates allocate order discount proportionally."""
        # Item 1: 400.00 (5% GST), Item 2: 600.00 (12% GST). Total items = 1000.00
        # Order discount = 200.00 (20%)
        # Item 1 gets 40% of discount = 80.00 -> Net 320.00
        # Item 2 gets 60% of discount = 120.00 -> Net 480.00
        order = self._create_order(
            items_subtotal=Decimal("1000.00"),
            total_discount=Decimal("200.00"),
            state=IndianStates.KARNATAKA,
        )
        OrderLineItem.objects.create(
            order=order,
            variant=self.variant1,
            quantity=2,
            product_name="Rasam Powder",
            variant_name="500g",
            sku=self.variant1.sku,
            weight_in_grams=500,
            mrp=Decimal("200.00"),
            unit_price=Decimal("200.00"),
            line_subtotal=Decimal("400.00"),
        )
        OrderLineItem.objects.create(
            order=order,
            variant=self.variant2,
            quantity=2,
            product_name="Biryani Masala",
            variant_name="200g",
            sku=self.variant2.sku,
            weight_in_grams=200,
            mrp=Decimal("300.00"),
            unit_price=Decimal("300.00"),
            line_subtotal=Decimal("600.00"),
        )

        invoice = InvoiceService.generate_invoice(order)

        self.assertEqual(invoice.items_subtotal, Decimal("1000.00"))
        self.assertEqual(invoice.total_discount, Decimal("200.00"))
        self.assertEqual(invoice.grand_total, Decimal("800.00"))

        lines = list(invoice.lines.order_by("created_at"))
        line1 = lines[0]
        line2 = lines[1]

        self.assertEqual(line1.discount_amount, Decimal("80.00"))
        self.assertEqual(line1.total_amount, Decimal("320.00"))
        # 320.00 / 1.05 = 304.76 taxable, 15.24 tax
        self.assertEqual(line1.taxable_amount, Decimal("304.76"))

        self.assertEqual(line2.discount_amount, Decimal("120.00"))
        self.assertEqual(line2.total_amount, Decimal("480.00"))
        # 480.00 / 1.12 = 428.57 taxable, 51.43 tax
        self.assertEqual(line2.taxable_amount, Decimal("428.57"))

        # Sum of lines equals invoice totals
        self.assertEqual(invoice.taxable_subtotal, line1.taxable_amount + line2.taxable_amount)
        self.assertEqual(
            invoice.taxable_subtotal + invoice.total_tax + invoice.shipping_fee,
            invoice.grand_total,
        )

    def test_5_intrastate_gst_discounted_splits_equally_cgst_sgst(self):
        """5. Intra-state supply splits tax equally into CGST and SGST with IGST zero."""
        order = self._create_order(
            items_subtotal=Decimal("500.00"),
            total_discount=Decimal("100.00"),
            state=IndianStates.KARNATAKA,
        )
        OrderLineItem.objects.create(
            order=order,
            variant=self.variant1,
            quantity=2,
            product_name="Rasam Powder",
            variant_name="500g",
            sku=self.variant1.sku,
            weight_in_grams=500,
            mrp=Decimal("250.00"),
            unit_price=Decimal("250.00"),
            line_subtotal=Decimal("500.00"),
        )

        invoice = InvoiceService.generate_invoice(order)

        self.assertFalse(invoice.is_interstate)
        self.assertEqual(invoice.igst_amount, Decimal("0.00"))
        self.assertGreater(invoice.cgst_amount, Decimal("0.00"))
        self.assertGreater(invoice.sgst_amount, Decimal("0.00"))
        self.assertEqual(invoice.cgst_amount + invoice.sgst_amount, invoice.total_tax)

    def test_6_interstate_gst_discounted_charges_full_igst(self):
        """6. Inter-state supply routes full discounted tax to IGST with CGST and SGST zero."""
        order = self._create_order(
            items_subtotal=Decimal("500.00"),
            total_discount=Decimal("100.00"),
            state=IndianStates.MAHARASHTRA,
        )
        OrderLineItem.objects.create(
            order=order,
            variant=self.variant1,
            quantity=2,
            product_name="Rasam Powder",
            variant_name="500g",
            sku=self.variant1.sku,
            weight_in_grams=500,
            mrp=Decimal("250.00"),
            unit_price=Decimal("250.00"),
            line_subtotal=Decimal("500.00"),
        )

        invoice = InvoiceService.generate_invoice(order)

        self.assertTrue(invoice.is_interstate)
        self.assertEqual(invoice.cgst_amount, Decimal("0.00"))
        self.assertEqual(invoice.sgst_amount, Decimal("0.00"))
        self.assertGreater(invoice.igst_amount, Decimal("0.00"))
        self.assertEqual(invoice.igst_amount, invoice.total_tax)

    def test_7_b2b_wholesale_invoice_with_discount_records_credentials_and_net_tax(self):
        """7. B2B wholesale orders record buyer GSTIN/PAN with properly discounted tax breakdown."""
        from apps.accounts.models import WholesaleProfile

        self.user.role = "WHOLESALE"
        self.user.save()
        WholesaleProfile.objects.create(
            user=self.user,
            company_name="Royal Spices Distributors",
            gstin="29ABCDE1234F1Z5",
            pan_number="ABCDE1234F",
        )

        order = self._create_order(
            items_subtotal=Decimal("2000.00"),
            total_discount=Decimal("200.00"),
            is_b2b=True,
            state=IndianStates.KARNATAKA,
        )
        OrderLineItem.objects.create(
            order=order,
            variant=self.variant1,
            quantity=10,
            product_name="Rasam Powder",
            variant_name="500g",
            sku=self.variant1.sku,
            weight_in_grams=500,
            mrp=Decimal("200.00"),
            unit_price=Decimal("200.00"),
            line_subtotal=Decimal("2000.00"),
        )

        invoice = InvoiceService.generate_invoice(order)

        self.assertTrue(invoice.is_b2b)
        self.assertEqual(invoice.buyer_gstin, "29ABCDE1234F1Z5")
        self.assertEqual(invoice.buyer_pan, "ABCDE1234F")
        self.assertEqual(invoice.buyer_company_name, "Royal Spices Distributors")
        self.assertEqual(invoice.grand_total, Decimal("1800.00"))
        self.assertEqual(
            invoice.taxable_subtotal + invoice.total_tax + invoice.shipping_fee,
            invoice.grand_total,
        )

    def test_8_zero_value_replacement_order_has_zero_taxable_and_zero_tax(self):
        """8. Zero-cost replacement orders (total_discount == items_subtotal) produce zero tax liability."""
        order = self._create_order(
            items_subtotal=Decimal("500.00"),
            total_discount=Decimal("500.00"),  # 100% discount for replacement
            shipping_fee=Decimal("0.00"),
            state=IndianStates.KARNATAKA,
        )
        OrderLineItem.objects.create(
            order=order,
            variant=self.variant1,
            quantity=2,
            product_name="Rasam Powder",
            variant_name="500g",
            sku=self.variant1.sku,
            weight_in_grams=500,
            mrp=Decimal("250.00"),
            unit_price=Decimal("250.00"),
            line_subtotal=Decimal("500.00"),
            pricing_tier_applied="REPLACEMENT",
        )

        invoice = InvoiceService.generate_invoice(order)

        self.assertEqual(invoice.items_subtotal, Decimal("500.00"))
        self.assertEqual(invoice.total_discount, Decimal("500.00"))
        self.assertEqual(invoice.grand_total, Decimal("0.00"))

        # Zero taxable value and zero tax liability
        self.assertEqual(invoice.taxable_subtotal, Decimal("0.00"))
        self.assertEqual(invoice.cgst_amount, Decimal("0.00"))
        self.assertEqual(invoice.sgst_amount, Decimal("0.00"))
        self.assertEqual(invoice.igst_amount, Decimal("0.00"))
        self.assertEqual(invoice.total_tax, Decimal("0.00"))

        line = invoice.lines.first()
        self.assertEqual(line.discount_amount, Decimal("500.00"))
        self.assertEqual(line.total_amount, Decimal("0.00"))
        self.assertEqual(line.taxable_amount, Decimal("0.00"))
        self.assertEqual(line.cgst_amount, Decimal("0.00"))
        self.assertEqual(line.sgst_amount, Decimal("0.00"))

        # Invariant strictly preserved: 0 + 0 + 0 = 0
        self.assertEqual(
            invoice.taxable_subtotal + invoice.total_tax + invoice.shipping_fee,
            invoice.grand_total,
        )

    def test_9_largest_remainder_multi_item_upward_rounding_edge_case(self):
        """9. Multi-item upward rounding (10, 10, 10, 1 with 0.02 disc) allocated exactly with no drift."""
        # 4 lines totaling 31.00 with 0.02 discount
        order = self._create_order(
            items_subtotal=Decimal("31.00"),
            total_discount=Decimal("0.02"),
            state=IndianStates.KARNATAKA,
        )
        for i, val in enumerate(
            [Decimal("10.00"), Decimal("10.00"), Decimal("10.00"), Decimal("1.00")]
        ):
            var = self._create_variant(f"Sample Spice {i+1}", f"SAMPLE-SPICE-{i+1}", val)
            OrderLineItem.objects.create(
                order=order,
                variant=var,
                quantity=1,
                product_name=f"Sample Spice {i+1}",
                variant_name="Pack",
                sku=f"SAMPLE-SPICE-{i+1}",
                weight_in_grams=100,
                mrp=val,
                unit_price=val,
                line_subtotal=val,
            )

        invoice = InvoiceService.generate_invoice(order)

        self.assertEqual(invoice.items_subtotal, Decimal("31.00"))
        self.assertEqual(invoice.total_discount, Decimal("0.02"))
        self.assertEqual(invoice.grand_total, Decimal("30.98"))

        lines = list(invoice.lines.all())
        total_line_disc = sum(line.discount_amount for line in lines)
        # CRITICAL INVARIANT: Sum of line discounts MUST EQUAL total discount exactly
        self.assertEqual(total_line_disc, Decimal("0.02"))

        # Individual line discounts must be non-negative and not exceed line gross
        for line in lines:
            self.assertGreaterEqual(line.discount_amount, Decimal("0.00"))
            self.assertLessEqual(line.discount_amount, line.order_line_item.line_subtotal)

        # Taxable amounts and total tax integrity
        self.assertEqual(
            sum(line.taxable_amount for line in lines),
            invoice.taxable_subtotal,
        )
        self.assertEqual(
            invoice.taxable_subtotal + invoice.total_tax + invoice.shipping_fee,
            invoice.grand_total,
        )

    def test_10_one_paisa_discount_across_many_lines(self):
        """10. Minimal 1 paisa (0.01) discount across 5 lines allocates to exactly one line."""
        order = self._create_order(
            items_subtotal=Decimal("100.00"),
            total_discount=Decimal("0.01"),
            state=IndianStates.KARNATAKA,
        )
        for i in range(5):
            var = self._create_variant(f"Pack {i+1}", f"PACK-SKU-{i+1}", Decimal("20.00"))
            OrderLineItem.objects.create(
                order=order,
                variant=var,
                quantity=1,
                product_name=f"Pack {i+1}",
                variant_name="200g",
                sku=f"PACK-SKU-{i+1}",
                weight_in_grams=200,
                mrp=Decimal("20.00"),
                unit_price=Decimal("20.00"),
                line_subtotal=Decimal("20.00"),
            )

        invoice = InvoiceService.generate_invoice(order)

        self.assertEqual(invoice.total_discount, Decimal("0.01"))
        lines = list(invoice.lines.all())
        total_disc = sum(line.discount_amount for line in lines)
        self.assertEqual(total_disc, Decimal("0.01"))

        # Exactly 1 line gets 0.01, other 4 get 0.00
        disc_counts = [line_item.discount_amount for line_item in lines]
        self.assertEqual(disc_counts.count(Decimal("0.01")), 1)
        self.assertEqual(disc_counts.count(Decimal("0.00")), 4)

        self.assertEqual(
            invoice.taxable_subtotal + invoice.total_tax + invoice.shipping_fee,
            invoice.grand_total,
        )

    def test_11_high_discount_nearly_full_order_value(self):
        """11. Deep discount (599.98 on 600.00) preserves non-negative net lines and statutory sums."""
        order = self._create_order(
            items_subtotal=Decimal("600.00"),
            total_discount=Decimal("599.98"),
            state=IndianStates.KARNATAKA,
        )
        for i, val in enumerate([Decimal("100.00"), Decimal("200.00"), Decimal("300.00")]):
            var = self._create_variant(f"Spice Item {i+1}", f"HIGH-DISC-{i+1}", val)
            OrderLineItem.objects.create(
                order=order,
                variant=var,
                quantity=1,
                product_name=f"Spice Item {i+1}",
                variant_name="Standard",
                sku=f"HIGH-DISC-{i+1}",
                weight_in_grams=100,
                mrp=val,
                unit_price=val,
                line_subtotal=val,
            )

        invoice = InvoiceService.generate_invoice(order)

        self.assertEqual(invoice.total_discount, Decimal("599.98"))
        self.assertEqual(invoice.grand_total, Decimal("0.02"))

        lines = list(invoice.lines.all())
        total_disc = sum(line.discount_amount for line in lines)
        self.assertEqual(total_disc, Decimal("599.98"))

        # Net totals must sum to grand total (0.02)
        self.assertEqual(sum(line.total_amount for line in lines), Decimal("0.02"))
        self.assertEqual(
            invoice.taxable_subtotal + invoice.total_tax + invoice.shipping_fee,
            invoice.grand_total,
        )

    def test_12_uneven_line_prices_and_quantities(self):
        """12. Uneven prices and quantities allocate discount proportionally without penny drift."""
        order = self._create_order(
            items_subtotal=Decimal("250.00"),
            total_discount=Decimal("37.50"),
            shipping_fee=Decimal("45.00"),
            state=IndianStates.KARNATAKA,
        )
        # Line 1: 3 * 33.33 = 99.99
        var_a = self._create_variant("Product A", "PROD-A-UNEVEN", Decimal("33.33"))
        OrderLineItem.objects.create(
            order=order,
            variant=var_a,
            quantity=3,
            product_name="Product A",
            variant_name="Small",
            sku="PROD-A-UNEVEN",
            weight_in_grams=100,
            mrp=Decimal("33.33"),
            unit_price=Decimal("33.33"),
            line_subtotal=Decimal("99.99"),
        )
        # Line 2: 7 * 14.28 = 99.96
        var_b = self._create_variant("Product B", "PROD-B-UNEVEN", Decimal("14.28"))
        OrderLineItem.objects.create(
            order=order,
            variant=var_b,
            quantity=7,
            product_name="Product B",
            variant_name="Bulk",
            sku="PROD-B-UNEVEN",
            weight_in_grams=200,
            mrp=Decimal("14.28"),
            unit_price=Decimal("14.28"),
            line_subtotal=Decimal("99.96"),
        )
        # Line 3: 1 * 50.05 = 50.05
        var_c = self._create_variant("Product C", "PROD-C-UNEVEN", Decimal("50.05"))
        OrderLineItem.objects.create(
            order=order,
            variant=var_c,
            quantity=1,
            product_name="Product C",
            variant_name="Special",
            sku="PROD-C-UNEVEN",
            weight_in_grams=150,
            mrp=Decimal("50.05"),
            unit_price=Decimal("50.05"),
            line_subtotal=Decimal("50.05"),
        )

        invoice = InvoiceService.generate_invoice(order)

        self.assertEqual(invoice.items_subtotal, Decimal("250.00"))
        self.assertEqual(invoice.total_discount, Decimal("37.50"))
        self.assertEqual(invoice.grand_total, Decimal("257.50"))  # 250 - 37.50 + 45.00

        lines = list(invoice.lines.all())
        total_disc = sum(line.discount_amount for line in lines)
        self.assertEqual(total_disc, Decimal("37.50"))

        self.assertEqual(
            sum(line.taxable_amount for line in lines),
            invoice.taxable_subtotal,
        )
        self.assertEqual(
            invoice.taxable_subtotal + invoice.total_tax + invoice.shipping_fee,
            invoice.grand_total,
        )
