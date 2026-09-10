from decimal import Decimal

from django.db.models import ProtectedError
from django.test import TestCase

from apps.accounts.models import IndianStates
from apps.inventory.services import InventoryService
from apps.inventory.tests.factories import create_variant
from apps.orders.services import CheckoutService
from apps.orders.tests.factories import (
    add_to_cart,
    create_order_address,
    create_order_user,
)


class OrderSnapshotImmutabilityTests(TestCase):
    def setUp(self):
        self.user = create_order_user()
        self.address = create_order_address(
            self.user,
            recipient_name="Original Recipient",
        )
        self.variant = create_variant("snap")
        InventoryService.add_stock(self.variant, 20)
        add_to_cart(self.user, self.variant, 2)
        self.order = CheckoutService.create_order_from_cart(
            user=self.user,
            shipping_address_id=self.address.id,
        )

    def test_address_modification_does_not_affect_order_snapshot(self):
        # Mutate the source Address record
        self.address.recipient_name = "Modified Recipient Name"
        self.address.phone_number = "9999999999"
        self.address.address_line_1 = "99 New Valley Road"
        self.address.city = "Bengaluru"
        self.address.state = IndianStates.MAHARASHTRA
        self.address.pincode = "560001"
        self.address.save()

        # Order must retain pristine snapshots
        self.order.refresh_from_db()
        self.assertEqual(self.order.shipping_recipient_name, "Original Recipient")
        self.assertEqual(self.order.shipping_phone_number, "+919876543201")
        self.assertEqual(self.order.shipping_address_line_1, "Devimane Ghat Road, Sirsi")
        self.assertEqual(self.order.shipping_city, "Sirsi")
        self.assertEqual(self.order.shipping_state, IndianStates.KARNATAKA)
        self.assertEqual(self.order.shipping_pincode, "581401")

    def test_address_deletion_preserves_order_flat_snapshot(self):
        # Delete source Address
        self.address.delete()

        self.order.refresh_from_db()
        self.assertIsNone(self.order.shipping_address)
        self.assertEqual(self.order.shipping_recipient_name, "Original Recipient")
        self.assertEqual(self.order.shipping_phone_number, "+919876543201")
        self.assertEqual(self.order.shipping_address_line_1, "Devimane Ghat Road, Sirsi")
        self.assertEqual(self.order.shipping_city, "Sirsi")
        self.assertEqual(self.order.shipping_state, IndianStates.KARNATAKA)
        self.assertEqual(self.order.shipping_pincode, "581401")

    def test_product_pricing_changes_do_not_affect_order_line_snapshot(self):
        line = self.order.lines.first()
        self.assertEqual(line.unit_price, Decimal("90.00"))
        self.assertEqual(line.mrp, Decimal("100.00"))
        self.assertEqual(line.line_subtotal, Decimal("180.00"))

        # Catalog manager modifies price, MRP, and product name
        self.variant.selling_price = Decimal("195.00")
        self.variant.mrp = Decimal("250.00")
        self.variant.save()

        product = self.variant.product
        product.name = "Altered Spice Name"
        product.save()

        # OrderLineItem remains immutable
        line.refresh_from_db()
        self.assertEqual(line.unit_price, Decimal("90.00"))
        self.assertEqual(line.mrp, Decimal("100.00"))
        self.assertEqual(line.line_subtotal, Decimal("180.00"))
        self.assertEqual(line.product_name, "Inventory product snap")
        self.assertEqual(line.sku, "INV-SNAP")

    def test_product_variant_deletion_is_protected(self):
        with self.assertRaises(ProtectedError):
            self.variant.delete()
