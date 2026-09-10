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


class CatalogPerformanceTests(TestCase):
    """
    Performance and anti-N+1 regression tests.
    Ensures query counts remain constant as products and variants scale.
    """

    def setUp(self):
        cache.clear()
        self.client = APIClient()

        self.category = Category.objects.create(name="Spices", slug="spices")

        # Create 10 products each with 3 variants and wholesale slabs
        for i in range(10):
            prod = Product.objects.create(
                category=self.category,
                name=f"Spice Item {i}",
                slug=f"spice-item-{i}",
                tier=Tier.RESERVE if i % 2 == 0 else Tier.EVERYDAY,
                form=Form.WHOLE,
                hsn_code="0904",
                gst_rate=Decimal("5.00"),
            )
            for j in range(3):
                v = ProductVariant.objects.create(
                    product=prod,
                    variant_name=f"Pack {j}",
                    sku=f"SKU-{i}-{j}",
                    weight_in_grams=(j + 1) * 100,
                    mrp=Decimal("200.00"),
                    selling_price=Decimal("160.00"),
                    sort_order=j,
                )
                WholesaleTierPricing.objects.create(
                    variant=v,
                    min_quantity=10,
                    wholesale_price_per_unit=Decimal("120.00"),
                )

        self.wholesale_user = User.objects.create_user(
            email="wholesale@dealer.com",
            phone_number="+919600000001",
            password="SecurePassword123!",
            role=Role.WHOLESALE_APPROVED,
        )
        WholesaleProfile.objects.create(
            user=self.wholesale_user,
            company_name="Dealer Corp",
            gstin="29ABCDE1234F1Z5",
            pan_number="ABCDE1234F",
            verification_status=VerificationStatus.APPROVED,
        )

    def tearDown(self):
        cache.clear()

    def test_product_list_query_count_retail_bounded(self):
        """
        Verify that listing 10 products with 30 variants does not trigger N+1 queries.
        Retail query count must be strictly <= 6 (count, products, categories, variants, images).
        """
        with self.assertNumQueries(4):
            # 1: count() for paginator
            # 2: products with select_related('category')
            # 3: prefetch variants
            # 4: prefetch images
            response = self.client.get("/api/v1/catalog/products/")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(len(data["data"]["results"]), 10)

    def test_product_detail_query_count_retail_bounded(self):
        """
        Verify that viewing product detail has fixed query count.
        """
        with self.assertNumQueries(4):
            # 1: product with select_related category
            # 2: prefetch variants
            # 3: prefetch images
            # 4: prefetch reviews
            response = self.client.get("/api/v1/catalog/products/spice-item-0/")
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_product_detail_query_count_wholesale_bounded(self):
        """
        Wholesale user prefetching wholesale_slabs adds exactly 1 prefetch query.
        """
        self.client.force_authenticate(user=self.wholesale_user)
        with self.assertNumQueries(5):
            # 1: product with select_related category
            # 2: prefetch variants
            # 3: prefetch images
            # 4: prefetch wholesale slabs
            # 5: prefetch reviews
            response = self.client.get("/api/v1/catalog/products/spice-item-0/")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertIn("wholesale_slabs", data["data"]["variants"][0])
