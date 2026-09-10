from django.test import TestCase
from django.conf import settings
from django.core.management import call_command
from rest_framework.test import APIClient
from pathlib import Path

from apps.catalog.models import Product, ProductImage, Category, Tier, Form
from apps.catalog.serializers import ProductListSerializer, ProductDetailSerializer


class ProductImageAuditTests(TestCase):
    """
    Automated regression tests verifying product images across catalog,
    detail serializers, cart serialization, and media filesystem existence.
    """

    @classmethod
    def setUpTestData(cls):
        call_command('seed_catalog')

    def setUp(self):
        self.client = APIClient()

    def test_all_products_have_active_images(self):
        """Verify all active products have at least one active ProductImage with a hero."""
        products = Product.objects.filter(is_active=True)
        self.assertEqual(products.count(), 12)

        for product in products:
            hero_image = product.images.filter(is_hero=True, is_active=True).first()
            self.assertIsNotNone(
                hero_image,
                f"Product '{product.name}' ({product.slug}) lacks an active hero image."
            )
            self.assertTrue(bool(hero_image.image))

    def test_product_list_serializer_includes_hero_image(self):
        """Verify ProductListSerializer outputs valid hero_image URLs."""
        res = self.client.get('/api/v1/catalog/products/')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        results = data.get('data', {}).get('results', [])
        self.assertEqual(len(results), 12)

        for item in results:
            hero_url = item.get('hero_image')
            self.assertIsNotNone(hero_url, f"Product '{item.get('name')}' returned null hero_image")
            self.assertIn('/media/products/', hero_url)

    def test_product_detail_serializer_includes_gallery_images(self):
        """Verify ProductDetailSerializer outputs gallery images."""
        product = Product.objects.filter(is_active=True).first()
        res = self.client.get(f'/api/v1/catalog/products/{product.slug}/')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        prod_data = data.get('data', {})
        images = prod_data.get('images', [])
        self.assertGreater(len(images), 0)
        self.assertTrue(any(img.get('is_hero') for img in images))

    def test_media_files_exist_on_disk(self):
        """Verify that files referenced by active ProductImages exist in MEDIA_ROOT."""
        media_root = Path(settings.MEDIA_ROOT)
        images = ProductImage.objects.filter(is_active=True)
        self.assertGreater(images.count(), 0)

        for img in images:
            file_path = media_root / img.image.name
            self.assertTrue(
                file_path.exists(),
                f"Image file on disk missing for Product '{img.product.name}': {file_path}"
            )

    def test_missing_image_graceful_fallback(self):
        """Verify serializer returns None instead of raising an exception if no images exist."""
        cat = Category.objects.first()
        dummy_product = Product.objects.create(
            name='No Image Spice',
            slug='no-image-spice',
            category=cat,
            tier=Tier.EVERYDAY,
            form=Form.WHOLE,
            is_active=True,
            packer_name='Bharat Masala',
            packer_address='Shimoga',
            best_before_guidance='12 months'
        )
        serializer = ProductListSerializer(dummy_product)
        self.assertIsNone(serializer.data.get('hero_image'))
