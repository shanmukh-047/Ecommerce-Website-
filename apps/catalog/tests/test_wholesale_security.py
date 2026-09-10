from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Role, User, VerificationStatus, WholesaleProfile
from apps.catalog.models import (
    Category,
    Form,
    Product,
    ProductVariant,
    Tier,
    WholesaleTierPricing,
)


class WholesalePricingSecurityTests(TestCase):
    """
    CRITICAL SECURITY TESTS:
    Ensures B2B wholesale pricing slabs are never exposed to anonymous shoppers,
    retail households, or unverified/pending wholesale applicants.
    """

    def setUp(self):
        cache.clear()
        self.client = APIClient()

        # Catalog setup
        self.category = Category.objects.create(name="Reserve Spices", slug="reserve-spices")
        self.product = Product.objects.create(
            category=self.category,
            name="Estate Sirsi Black Pepper",
            slug="estate-sirsi-black-pepper",
            tier=Tier.RESERVE,
            form=Form.WHOLE,
            hsn_code="0904",
            gst_rate=Decimal("5.00"),
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_name="1kg Bulk Bag",
            sku="BMP-PEP-RSV-1KG",
            weight_in_grams=1000,
            mrp=Decimal("1200.00"),
            selling_price=Decimal("950.00"),
        )
        self.slab1 = WholesaleTierPricing.objects.create(
            variant=self.variant,
            min_quantity=10,
            wholesale_price_per_unit=Decimal("780.00"),
        )
        self.slab2 = WholesaleTierPricing.objects.create(
            variant=self.variant,
            min_quantity=25,
            wholesale_price_per_unit=Decimal("720.00"),
        )

        # Users
        self.retail_user = User.objects.create_user(
            email="retail@consumer.com",
            phone_number="+919800000001",
            password="SecurePassword123!",
            role=Role.CUSTOMER,
        )

        self.pending_user = User.objects.create_user(
            email="pending@grocery.com",
            phone_number="+919800000002",
            password="SecurePassword123!",
            role=Role.WHOLESALE_PENDING,
        )
        WholesaleProfile.objects.create(
            user=self.pending_user,
            company_name="Pending Grocery Store",
            gstin="29ABCDE1234F1Z5",
            pan_number="ABCDE1234F",
            verification_status=VerificationStatus.PENDING,
        )

        self.approved_user = User.objects.create_user(
            email="approved@distributor.com",
            phone_number="+919800000003",
            password="SecurePassword123!",
            role=Role.WHOLESALE_APPROVED,
        )
        WholesaleProfile.objects.create(
            user=self.approved_user,
            company_name="Approved Malenadu Traders",
            gstin="29ABCDE1234F1Z5",
            pan_number="ABCDE1234F",
            verification_status=VerificationStatus.APPROVED,
        )

    def tearDown(self):
        cache.clear()

    def test_anonymous_user_cannot_view_wholesale_slabs_in_list(self):
        """Anonymous user listing products must not receive wholesale_slabs data."""
        response = self.client.get("/api/v1/catalog/products/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        results = data["data"]["results"]
        self.assertGreater(len(results), 0)
        variant = results[0]["variants"][0]
        self.assertNotIn("wholesale_slabs", variant)

    def test_anonymous_user_cannot_view_wholesale_slabs_in_detail(self):
        """Anonymous user viewing product detail must not receive wholesale_slabs data."""
        response = self.client.get(f"/api/v1/catalog/products/{self.product.slug}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        variant = data["data"]["variants"][0]
        self.assertNotIn("wholesale_slabs", variant)

    def test_retail_customer_cannot_view_wholesale_slabs(self):
        """Authenticated retail customer must not receive wholesale_slabs data."""
        self.client.force_authenticate(user=self.retail_user)
        response = self.client.get(f"/api/v1/catalog/products/{self.product.slug}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        variant = data["data"]["variants"][0]
        self.assertNotIn("wholesale_slabs", variant)

    def test_pending_wholesale_customer_cannot_view_wholesale_slabs(self):
        """
        Wholesale applicant whose KYC is still PENDING must not receive wholesale_slabs data.
        """
        self.client.force_authenticate(user=self.pending_user)
        response = self.client.get(f"/api/v1/catalog/products/{self.product.slug}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        variant = data["data"]["variants"][0]
        self.assertNotIn("wholesale_slabs", variant)

    def test_approved_wholesale_customer_receives_wholesale_slabs(self):
        """
        Authenticated customer with verified WHOLESALE_APPROVED account receives
        the full wholesale slab breakdown with MOQ tiers and unit pricing.
        """
        self.client.force_authenticate(user=self.approved_user)
        response = self.client.get(f"/api/v1/catalog/products/{self.product.slug}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        variant = data["data"]["variants"][0]
        self.assertIn("wholesale_slabs", variant)
        slabs = variant["wholesale_slabs"]
        self.assertEqual(len(slabs), 2)
        self.assertEqual(slabs[0]["min_quantity"], 10)
        self.assertEqual(slabs[0]["wholesale_price_per_unit"], "780.00")
        self.assertEqual(slabs[1]["min_quantity"], 25)
        self.assertEqual(slabs[1]["wholesale_price_per_unit"], "720.00")
