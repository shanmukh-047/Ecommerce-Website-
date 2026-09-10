"""
Automated End-to-End Verification of Bharat Masala Product Catalog & Cart Integration
"""

import os
import sys
from pathlib import Path
import django

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.test import RequestFactory
from apps.catalog.views import CategoryListView, ProductListView, ProductDetailView
from apps.cart.views import CartView, CartItemListCreateView

def run_tests():
    rf = RequestFactory()
    passed = 0
    total = 0

    print("=" * 60)
    print("BHARAT MASALA CATALOG & VARIANT INTEGRATION VERIFICATION")
    print("=" * 60)

    # 1. Categories List
    total += 1
    req = rf.get('/api/v1/catalog/categories/')
    res = CategoryListView.as_view()(req)
    assert res.status_code == 200, f"Categories failed with status {res.status_code}"
    categories = res.data
    assert len(categories) >= 4, f"Expected at least 4 categories, got {len(categories)}"
    print(f"[{passed+1}/{total}] PASS: Categories list returned {len(categories)} categories")
    passed += 1

    # 2. Products List & Pagination Envelope
    total += 1
    req = rf.get('/api/v1/catalog/products/')
    res = ProductListView.as_view()(req)
    assert res.status_code == 200, f"Products list failed with status {res.status_code}"
    data = res.data
    assert 'count' in data and 'results' in data, "Expected paginated envelope"
    assert data['count'] >= 12, f"Expected at least 12 products, got {data['count']}"
    products = data['results']
    print(f"[{passed+1}/{total}] PASS: Products list returned {data['count']} items with valid pagination envelope")
    passed += 1

    # 3. ProductListSerializer fields integrity
    total += 1
    sample = products[0]
    required_keys = ['id', 'name', 'slug', 'category', 'tier', 'form', 'origin_region', 'hero_image', 'starting_price', 'variants']
    for k in required_keys:
        assert k in sample, f"Missing key '{k}' in product list serializer output"
    assert len(sample['variants']) > 0, "Product has no variants"
    print(f"[{passed+1}/{total}] PASS: ProductListSerializer fields validated on sample: '{sample['name']}'")
    passed += 1

    # 4. Category Filter
    total += 1
    req = rf.get('/api/v1/catalog/products/?category=pure-spices')
    res = ProductListView.as_view()(req)
    assert res.status_code == 200
    for p in res.data['results']:
        assert p['category']['slug'] == 'pure-spices', f"Unexpected category slug {p['category']['slug']}"
    print(f"[{passed+1}/{total}] PASS: Filter ?category=pure-spices returned {res.data['count']} matched items")
    passed += 1

    # 5. Quality Tier Filter
    total += 1
    req = rf.get('/api/v1/catalog/products/?tier=RESERVE')
    res = ProductListView.as_view()(req)
    assert res.status_code == 200
    for p in res.data['results']:
        assert p['tier'] == 'RESERVE', f"Unexpected tier {p['tier']}"
    print(f"[{passed+1}/{total}] PASS: Filter ?tier=RESERVE returned {res.data['count']} matched items")
    passed += 1

    # 6. Spice Form Filter
    total += 1
    req = rf.get('/api/v1/catalog/products/?form=WHOLE')
    res = ProductListView.as_view()(req)
    assert res.status_code == 200
    for p in res.data['results']:
        assert p['form'] == 'WHOLE', f"Unexpected form {p['form']}"
    print(f"[{passed+1}/{total}] PASS: Filter ?form=WHOLE returned {res.data['count']} matched items")
    passed += 1

    # 7. Search Filter
    total += 1
    req = rf.get('/api/v1/catalog/products/?search=pepper')
    res = ProductListView.as_view()(req)
    assert res.status_code == 200
    assert res.data['count'] > 0, "Search for 'pepper' returned no products"
    print(f"[{passed+1}/{total}] PASS: Search ?search=pepper returned {res.data['count']} matched items")
    passed += 1

    # 8. Ordering Filter
    total += 1
    req_asc = rf.get('/api/v1/catalog/products/?ordering=price_low_to_high')
    res_asc = ProductListView.as_view()(req_asc)
    req_desc = rf.get('/api/v1/catalog/products/?ordering=price_high_to_low')
    res_desc = ProductListView.as_view()(req_desc)
    asc_first_price = float(res_asc.data['results'][0]['starting_price'])
    desc_first_price = float(res_desc.data['results'][0]['starting_price'])
    assert asc_first_price <= desc_first_price, f"Asc price {asc_first_price} > Desc price {desc_first_price}"
    print(f"[{passed+1}/{total}] PASS: Ordering verified: Lowest ₹{asc_first_price} vs Highest ₹{desc_first_price}")
    passed += 1

    # 9. ProductDetailView & Legal Metrology
    total += 1
    slug = sample['slug']
    req_det = rf.get(f'/api/v1/catalog/products/{slug}/')
    res_det = ProductDetailView.as_view()(req_det, slug=slug)
    assert res_det.status_code == 200, f"Detail view failed with {res_det.status_code}"
    det = res_det.data
    assert 'legal_metrology' in det, "Missing legal_metrology in detail serializer"
    lm = det['legal_metrology']
    assert lm.get('fssai_license') is not None, "Missing fssai_license in legal_metrology"
    assert lm.get('hsn_code') is not None, "Missing hsn_code in legal_metrology"
    assert lm.get('gst_rate') is not None, "Missing gst_rate in legal_metrology"
    print(f"[{passed+1}/{total}] PASS: ProductDetailView verified for '{slug}' with FSSAI license: {lm.get('fssai_license')}")
    passed += 1

    # 10. Cart Item Add via Catalog Variant ID
    total += 1
    variant_id = sample['variants'][0]['id']
    req_cart = rf.post('/api/v1/cart/items/', {'variant_id': str(variant_id), 'quantity': 2}, content_type='application/json')
    # Add guest cart cookie simulation or anonymous session
    from django.contrib.sessions.middleware import SessionMiddleware
    from django.contrib.auth.models import AnonymousUser
    req_cart.user = AnonymousUser()
    req_cart.COOKIES = {}
    
    # We call CartItemListCreateView
    res_cart = CartItemListCreateView.as_view()(req_cart)
    assert res_cart.status_code in [200, 201], f"Add to cart returned {res_cart.status_code}: {res_cart.data}"
    cart_items = res_cart.data['cart']['items']
    matching = [item for item in cart_items if str(item['variant_id']) == str(variant_id)]
    assert len(matching) > 0, "Added variant not found in cart items"
    print(f"[{passed+1}/{total}] PASS: Catalog variant {variant_id} successfully added to cart ({matching[0]['quantity']} units, total ₹{matching[0]['line_total']})")
    passed += 1

    print("=" * 60)
    print(f"ALL {passed}/{total} INTEGRATION TESTS PASSED CLEANLY!")
    print("=" * 60)

if __name__ == '__main__':
    run_tests()
