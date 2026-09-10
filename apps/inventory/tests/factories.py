from decimal import Decimal

from apps.catalog.models import Category, Form, Product, ProductVariant, Tier


def create_variant(suffix="one"):
    category = Category.objects.create(name=f"Inventory {suffix}", slug=f"inventory-{suffix}")
    product = Product.objects.create(
        category=category,
        name=f"Inventory product {suffix}",
        slug=f"inventory-product-{suffix}",
        tier=Tier.EVERYDAY,
        form=Form.GROUND,
        hsn_code="0910",
    )
    return ProductVariant.objects.create(
        product=product,
        variant_name="100g pack",
        sku=f"INV-{suffix.upper()}",
        mrp=Decimal("100.00"),
        selling_price=Decimal("90.00"),
    )
