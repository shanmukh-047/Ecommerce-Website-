import os
import shutil
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.catalog.models import Product, ProductImage

PRODUCT_IMAGE_SPECS = {
    'malabar-black-pepper-bold': {
        'hero_src': '02cc425f-d249-4706-98f7-fa88aaa625bd/5f01f225c9ca4ca680f93d049dcda804.jpg',
        'gallery_src': 'ff183ebd-c6dc-4cb6-8073-067f6b7b5a43/922fc74c9ed04dd8a263645548d99cc2.jpg',
        'alt_text': 'Malabar Black Pepper (Garbled Extra Bold) - Tellicherry 550GL+ sun-dried berries',
    },
    'wayanad-green-cardamom-jumbo': {
        'hero_src': '7fbb60eb-a975-435a-b9d1-d6b3eb01f54b/9d21e8caca0c4bf5be0b4a49116ba49c.jpg',
        'gallery_src': 'c10d1f9c-0f53-4a28-8e60-b22c0269d509/e06538e60e5346c991f6bfdb59659fa2.jpg',
        'alt_text': 'Wayanad Green Cardamom (8mm Jumbo Pods) - High-altitude rainforest canopy harvest',
    },
    'salem-pure-turmeric-powder': {
        'hero_src': 'dc27bcf7-e920-4bee-963b-e5460e6ee0e3/a4474350241a4fa4aa423276c9cf14dd.jpg',
        'gallery_src': 'e3a786df-51d3-4514-86ba-1492e244eb86/397312e13b0c4098a8638fb411567847.jpg',
        'alt_text': 'Salem Pure Turmeric Powder (5.2% High Curcumin) - Cold-milled golden rhizomes',
    },
    'kashmiri-chilli-powder-natural': {
        'hero_src': '72773c1e-3204-42f5-b6ae-0748e6072bb9/b00a0e0fefe8466ab86ef7eb30091142.jpg',
        'gallery_src': 'ea168052-8d34-4440-8565-3e04aa914940/4ea109b9d3d7493f94e93fa3addd7f69.jpg',
        'alt_text': 'Kashmiri Deggi Chilli Powder (Vibrant Natural Red) - Stone-ground mild red peppers',
    },
    'kerala-handpicked-clove-buds': {
        'hero_src': '44dc3620-223a-4522-9842-965e1483bf0a/e73bdd0a8fcc4f71a35d75623f7c2dd6.jpg',
        'gallery_src': 'a362c874-34f8-4e25-9120-0e608c0c0e35/c7ab310f6566405eb3f7865ff9cfb78b.jpg',
        'alt_text': 'Zanzibar Clove Buds (Hand-Picked Hand-Sorted) - Intact crowns with eugenol aroma',
    },
    'malabar-biryani-whole-spice-potli': {
        'hero_src': '6653da74-78e6-42bf-8014-24921131144b/316d9581e7e24bb0be6a97352d0a460c.jpg',
        'gallery_src': '89392372-6c4a-4b9d-aa9b-8a82f93304b2/2a7467aa39f0426f8ea12bcf283e3caa.jpg',
        'alt_text': 'Malabar Biryani Whole Spice Potli - Authentic Thalassery spice route blend',
    },
    'royal-shahi-garam-masala': {
        'hero_src': '7ca685cd-25d0-44f2-92e2-9ede3fc89a8f/08f2365e283d4d928fb42b5e1b5981c8.jpg',
        'gallery_src': '86e9e36f-55b3-420c-93e7-3288c4a95865/8d3644e9895c4259be71c4b052d15fc8.jpg',
        'alt_text': 'Royal Shahi Garam Masala (18 Rare Spices) - Artisanal heirloom whole spice blend',
    },
    'malenadu-traditional-sambar-masala': {
        'hero_src': 'e1273a68-155a-427f-bc7b-0e69cf4a5afe/eb9c309742ab43f7b751fad856ece2e6.jpg',
        'gallery_src': '0c58aacd-930a-4b59-a7ea-d96ebbc0abb9/432632e9b565426684ed8464bcd47dbe.jpg',
        'alt_text': 'Malenadu Traditional Sambar Masala - 14-spice slow roasted heritage recipe',
    },
    'roasted-dhaniya-coriander-powder': {
        'hero_src': 'ff183ebd-c6dc-4cb6-8073-067f6b7b5a43/922fc74c9ed04dd8a263645548d99cc2.jpg',
        'gallery_src': 'df3047c1-f91a-4bc2-b0c1-771359c69274/ed2781758c7548059738f048944a114b.jpg',
        'alt_text': 'Roasted Dhaniya (Coriander) Powder - Cast iron roasted aromatic seed powder',
    },
    'malenadu-whole-cashews-w240': {
        'hero_src': 'c10d1f9c-0f53-4a28-8e60-b22c0269d509/e06538e60e5346c991f6bfdb59659fa2.jpg',
        'gallery_src': '4023c962-8a21-45c3-836b-afe718c46963/e67682fb0f144048840717dfab05e679.jpg',
        'alt_text': 'Malenadu Coastal Whole Cashew Nuts (W240 Jumbo) - Hand-shelled crunchy cashews',
    },
    'royal-kashmiri-shahi-jeera': {
        'hero_src': 'e3a786df-51d3-4514-86ba-1492e244eb86/397312e13b0c4098a8638fb411567847.jpg',
        'gallery_src': '02cc425f-d249-4706-98f7-fa88aaa625bd/5f01f225c9ca4ca680f93d049dcda804.jpg',
        'alt_text': 'Royal Kashmiri Shahi Jeera (Caraway Seeds) - Wild alpine meadow harvest',
    },
    'sweet-lucknowi-saunf-fennel': {
        'hero_src': 'ea168052-8d34-4440-8565-3e04aa914940/4ea109b9d3d7493f94e93fa3addd7f69.jpg',
        'gallery_src': '7fbb60eb-a975-435a-b9d1-d6b3eb01f54b/9d21e8caca0c4bf5be0b4a49116ba49c.jpg',
        'alt_text': 'Sweet Lucknowi Saunf (Fennel Seeds) - Slender sweet variyali seeds',
    },
}

class Command(BaseCommand):
    help = 'Links authentic estate product photographs to all active products in the database.'

    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT)
        products_media_dir = media_root / 'products'

        total_linked = 0
        for slug, spec in PRODUCT_IMAGE_SPECS.items():
            product = Product.objects.filter(slug=slug).first()
            if not product:
                self.stdout.write(self.style.WARNING(f'Product {slug} not found in DB.'))
                continue

            target_dir = products_media_dir / str(product.id)
            target_dir.mkdir(parents=True, exist_ok=True)

            # 1. Hero Image
            hero_src = products_media_dir / spec['hero_src']
            hero_target_file = target_dir / 'hero.jpg'
            if hero_src.exists() and not hero_target_file.exists():
                shutil.copy2(hero_src, hero_target_file)
            elif not hero_src.exists() and not hero_target_file.exists():
                self.stdout.write(self.style.ERROR(f'Source hero not found: {hero_src}'))
                continue

            hero_rel_path = f'products/{product.id}/hero.jpg'
            hero_img, created = ProductImage.objects.update_or_create(
                product=product,
                is_hero=True,
                defaults={
                    'image': hero_rel_path,
                    'alt_text': spec['alt_text'],
                    'sort_order': 0,
                    'is_active': True,
                }
            )

            # 2. Gallery Image (Secondary)
            gallery_src = products_media_dir / spec['gallery_src']
            gallery_target_file = target_dir / 'gallery_1.jpg'
            if gallery_src.exists() and not gallery_target_file.exists():
                shutil.copy2(gallery_src, gallery_target_file)

            if gallery_target_file.exists():
                gallery_rel_path = f'products/{product.id}/gallery_1.jpg'
                ProductImage.objects.update_or_create(
                    product=product,
                    is_hero=False,
                    sort_order=1,
                    defaults={
                        'image': gallery_rel_path,
                        'alt_text': f'{product.name} - Terroir & Packaging Details',
                        'is_active': True,
                    }
                )

            total_linked += 1
            self.stdout.write(self.style.SUCCESS(f'Linked images for: {product.name} ({product.slug})'))

        self.stdout.write(self.style.SUCCESS(f'Successfully linked images for {total_linked} products.'))
