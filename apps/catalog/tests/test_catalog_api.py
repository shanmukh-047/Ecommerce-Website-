from decimal import Decimal
from io import BytesIO

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient

from apps.catalog.models import (
    Category,
    Form,
    Product,
    ProductImage,
    ProductVariant,
    Tier,
)


def make_test_image(name="test_img.jpg"):
    f = BytesIO()
    im = Image.new("RGB", (60, 60), color="orange")
    im.save(f, "JPEG")
    f.seek(0)
    return SimpleUploadedFile(name, f.read(), content_type="image/jpeg")


class CatalogAPITests(TestCase):
    """
    Comprehensive tests for Category and Product browsing, filtering,
    sorting, pagination, and envelope formatting.
    """

    def setUp(self):
        cache.clear()
        self.client = APIClient()

        # Categories
        self.cat_spices = Category.objects.create(name="Spices", slug="spices", sort_order=1)
        self.cat_blends = Category.objects.create(
            name="Signature Blends",
            slug="signature-blends",
            parent=self.cat_spices,
            sort_order=2,
        )
        self.cat_dryfruits = Category.objects.create(
            name="Dry Fruits", slug="dry-fruits", sort_order=3
        )
        self.cat_inactive = Category.objects.create(
            name="Inactive Category", slug="inactive-cat", is_active=False
        )

        # Products
        self.prod_pepper = Product.objects.create(
            category=self.cat_spices,
            name="Sirsi Bold Black Pepper",
            slug="sirsi-bold-black-pepper",
            tier=Tier.RESERVE,
            form=Form.WHOLE,
            short_description="Sun-dried estate Malenadu black pepper.",
            origin_region="Sirsi, Karnataka",
            is_featured_from_home=True,
            is_bestseller=True,
            hsn_code="0904",
            gst_rate=Decimal("5.00"),
        )
        self.variant_pepper_100g = ProductVariant.objects.create(
            product=self.prod_pepper,
            variant_name="100g Jar",
            sku="BMP-PEP-100G",
            weight_in_grams=100,
            mrp=Decimal("150.00"),
            selling_price=Decimal("120.00"),
            sort_order=1,
        )
        self.variant_pepper_250g = ProductVariant.objects.create(
            product=self.prod_pepper,
            variant_name="250g Pouch",
            sku="BMP-PEP-250G",
            weight_in_grams=250,
            mrp=Decimal("350.00"),
            selling_price=Decimal("280.00"),
            sort_order=2,
        )
        self.hero_pepper = ProductImage.objects.create(
            product=self.prod_pepper,
            image=make_test_image("pepper_hero.jpg"),
            is_hero=True,
            is_active=True,
        )

        self.prod_saaru = Product.objects.create(
            category=self.cat_blends,
            name="Malenadu Saaru Pudi",
            slug="malenadu-saaru-pudi",
            tier=Tier.RESERVE,
            form=Form.BLEND,
            short_description="Heirloom aromatic rasam powder.",
            origin_region="Shimoga, Karnataka",
            is_featured_from_home=False,
            is_bestseller=True,
            hsn_code="0910",
            gst_rate=Decimal("5.00"),
        )
        self.variant_saaru_250g = ProductVariant.objects.create(
            product=self.prod_saaru,
            variant_name="250g Eco-Box",
            sku="BMP-SRP-250G",
            weight_in_grams=250,
            mrp=Decimal("250.00"),
            selling_price=Decimal("210.00"),
            sort_order=1,
        )

        self.prod_everyday_turmeric = Product.objects.create(
            category=self.cat_spices,
            name="Everyday Fresh Turmeric Powder",
            slug="everyday-fresh-turmeric",
            tier=Tier.EVERYDAY,
            form=Form.GROUND,
            short_description="High curcumin daily kitchen turmeric.",
            origin_region="Malenadu, Karnataka",
            is_featured_from_home=False,
            is_bestseller=False,
            hsn_code="0910",
            gst_rate=Decimal("5.00"),
        )
        self.variant_turmeric_500g = ProductVariant.objects.create(
            product=self.prod_everyday_turmeric,
            variant_name="500g Value Pack",
            sku="BMP-TUR-500G",
            weight_in_grams=500,
            mrp=Decimal("180.00"),
            selling_price=Decimal("150.00"),
            sort_order=1,
        )

        self.prod_inactive = Product.objects.create(
            category=self.cat_spices,
            name="Archived Old Spice",
            slug="archived-old-spice",
            tier=Tier.EVERYDAY,
            form=Form.WHOLE,
            is_active=False,
            hsn_code="0904",
        )

    def tearDown(self):
        cache.clear()

    def test_category_list_api(self):
        """Verify category listing returns active root categories with subcategories."""
        response = self.client.get("/api/v1/catalog/categories/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        res_json = response.json()
        self.assertTrue(res_json["success"])
        categories = res_json["data"]
        # Only active root categories: Spices & Dry Fruits (not inactive or children directly at root)
        slugs = [c["slug"] for c in categories]
        self.assertIn("spices", slugs)
        self.assertIn("dry-fruits", slugs)
        self.assertNotIn("inactive-cat", slugs)

        # Check subcategories nesting under Spices
        spices = next(c for c in categories if c["slug"] == "spices")
        sub_slugs = [sc["slug"] for sc in spices["subcategories"]]
        self.assertIn("signature-blends", sub_slugs)

    def test_category_detail_api(self):
        """Verify category retrieval by slug and 404 handling."""
        response = self.client.get("/api/v1/catalog/categories/signature-blends/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        res_json = response.json()
        self.assertEqual(res_json["data"]["name"], "Signature Blends")

        # 404 for nonexistent or inactive
        response_404 = self.client.get("/api/v1/catalog/categories/non-existent-slug/")
        self.assertEqual(response_404.status_code, status.HTTP_404_NOT_FOUND)

        response_inactive = self.client.get("/api/v1/catalog/categories/inactive-cat/")
        self.assertEqual(response_inactive.status_code, status.HTTP_404_NOT_FOUND)

    def test_product_list_active_and_envelope(self):
        """Verify product list only shows active products with proper envelope structure."""
        response = self.client.get("/api/v1/catalog/products/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        res_json = response.json()
        self.assertTrue(res_json["success"])
        self.assertIn("request_id", res_json)
        data = res_json["data"]
        self.assertEqual(data["count"], 3)  # pepper, saaru, turmeric (not inactive)
        slugs = [p["slug"] for p in data["results"]]
        self.assertNotIn("archived-old-spice", slugs)

    def test_product_list_filter_by_parent_category(self):
        """Filtering by parent category 'spices' returns items in spices and subcategories."""
        response = self.client.get("/api/v1/catalog/products/?category=spices")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json()["data"]["results"]
        # Both Pepper (spices) and Saaru Pudi (signature-blends) + Turmeric (spices) match
        self.assertEqual(len(results), 3)

    def test_product_list_filter_by_subcategory(self):
        """Filtering by subcategory 'signature-blends' returns only blended products."""
        response = self.client.get("/api/v1/catalog/products/?category=signature-blends")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json()["data"]["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["slug"], "malenadu-saaru-pudi")

    def test_product_list_filter_by_tier(self):
        """Verify tier filtering (RESERVE vs EVERYDAY)."""
        response_res = self.client.get("/api/v1/catalog/products/?tier=RESERVE")
        self.assertEqual(response_res.status_code, status.HTTP_200_OK)
        self.assertEqual(response_res.json()["data"]["count"], 2)

        response_ev = self.client.get("/api/v1/catalog/products/?tier=EVERYDAY")
        self.assertEqual(response_ev.status_code, status.HTTP_200_OK)
        self.assertEqual(response_ev.json()["data"]["count"], 1)
        self.assertEqual(
            response_ev.json()["data"]["results"][0]["slug"], "everyday-fresh-turmeric"
        )

    def test_product_list_filter_by_form(self):
        """Verify form filtering (WHOLE, GROUND, BLEND, RAW)."""
        response = self.client.get("/api/v1/catalog/products/?form=BLEND")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json()["data"]["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["slug"], "malenadu-saaru-pudi")

    def test_product_list_filter_by_featured_and_bestseller(self):
        """Verify featured from home and bestseller filters."""
        resp_feat = self.client.get("/api/v1/catalog/products/?featured=true")
        self.assertEqual(resp_feat.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_feat.json()["data"]["count"], 1)
        self.assertEqual(resp_feat.json()["data"]["results"][0]["slug"], "sirsi-bold-black-pepper")

        resp_best = self.client.get("/api/v1/catalog/products/?bestseller=true")
        self.assertEqual(resp_best.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_best.json()["data"]["count"], 2)

    def test_product_list_search(self):
        """Verify substring search across name, description, and origin."""
        response = self.client.get("/api/v1/catalog/products/?search=Sirsi")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["count"], 1)
        self.assertEqual(response.json()["data"]["results"][0]["slug"], "sirsi-bold-black-pepper")

    def test_product_list_ordering_price(self):
        """Verify price_low_to_high and price_high_to_low ordering."""
        resp_low = self.client.get("/api/v1/catalog/products/?ordering=price_low_to_high")
        self.assertEqual(resp_low.status_code, status.HTTP_200_OK)
        results_low = resp_low.json()["data"]["results"]
        slugs_low = [p["slug"] for p in results_low]
        self.assertEqual(slugs_low[0], "sirsi-bold-black-pepper")
        self.assertEqual(slugs_low[1], "everyday-fresh-turmeric")
        self.assertEqual(slugs_low[2], "malenadu-saaru-pudi")

        resp_high = self.client.get("/api/v1/catalog/products/?ordering=price_high_to_low")
        self.assertEqual(resp_high.status_code, status.HTTP_200_OK)
        results_high = resp_high.json()["data"]["results"]
        slugs_high = [p["slug"] for p in results_high]
        self.assertEqual(slugs_high[0], "sirsi-bold-black-pepper")
        self.assertEqual(slugs_high[1], "malenadu-saaru-pudi")
        self.assertEqual(slugs_high[2], "everyday-fresh-turmeric")

    def test_product_detail_api(self):
        """Verify single product retrieval with all pack-sizes, legal metrology, and gallery."""
        response = self.client.get("/api/v1/catalog/products/sirsi-bold-black-pepper/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        res_json = response.json()
        self.assertTrue(res_json["success"])
        data = res_json["data"]
        self.assertEqual(data["name"], "Sirsi Bold Black Pepper")
        self.assertEqual(len(data["variants"]), 2)
        self.assertEqual(len(data["images"]), 1)
        self.assertIsNotNone(data.get("hero_image"))
        self.assertIn("media/products/", data["hero_image"])
        self.assertEqual(data["legal_metrology"]["hsn_code"], "0904")
        self.assertEqual(data["legal_metrology"]["gst_rate"], "5.00")
        self.assertEqual(data["reviews_summary"]["total_reviews"], 0)

    def test_product_detail_404(self):
        """Ensure non-existent product or inactive product returns 404."""
        response_missing = self.client.get("/api/v1/catalog/products/unknown-pepper/")
        self.assertEqual(response_missing.status_code, status.HTTP_404_NOT_FOUND)

        response_inactive = self.client.get("/api/v1/catalog/products/archived-old-spice/")
        self.assertEqual(response_inactive.status_code, status.HTTP_404_NOT_FOUND)
