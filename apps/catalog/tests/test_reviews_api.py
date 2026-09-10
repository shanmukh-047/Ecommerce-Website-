from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.catalog.models import (
    Category,
    Form,
    ModerationStatus,
    Product,
    ProductReview,
    ProductVariant,
    Tier,
)
from apps.orders.models import Order, OrderLineItem, OrderStatus


class ReviewAPITests(TestCase):
    """
    Tests customer review submission, rating bounds, verified purchase security,
    PII name masking, public catalog isolation, and staff moderation workflows.
    """

    def setUp(self):
        cache.clear()
        self.client = APIClient()

        # Catalog setup
        self.category = Category.objects.create(name="Spices", slug="spices")
        self.product = Product.objects.create(
            category=self.category,
            name="Sirsi Bold Black Pepper",
            slug="sirsi-bold-black-pepper",
            tier=Tier.RESERVE,
            form=Form.WHOLE,
            hsn_code="0904",
            gst_rate=Decimal("5.00"),
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_name="250g",
            sku="PEPPER-250G",
            weight_in_grams=250,
            mrp=Decimal("350.00"),
            selling_price=Decimal("350.00"),
        )

        # Users
        self.reviewer1 = User.objects.create_user(
            email="anand.hegde@example.com",
            phone_number="+919700000001",
            password="SecurePassword123!",
            first_name="Anand",
            last_name="Hegde",
            role=Role.CUSTOMER,
        )

        self.reviewer2 = User.objects.create_user(
            email="sudha.rao@example.com",
            phone_number="+919700000002",
            password="SecurePassword123!",
            first_name="Sudha",
            last_name="Rao",
            role=Role.CUSTOMER,
        )

        self.staff_user = User.objects.create_user(
            email="moderator@bharathmasala.com",
            phone_number="+919700000003",
            password="SecurePassword123!",
            role=Role.STAFF,
            is_staff=True,
        )

        # Create one existing approved review and one pending review
        self.approved_review = ProductReview.objects.create(
            product=self.product,
            user=self.reviewer1,
            rating=5,
            title="Incomparable aroma",
            review_body="The true taste of Malenadu. Wonderful packaging.",
            moderation_status=ModerationStatus.APPROVED,
        )

        self.pending_review = ProductReview.objects.create(
            product=self.product,
            user=self.reviewer2,
            rating=4,
            title="Good quality",
            review_body="Very fresh pepper corns.",
            moderation_status=ModerationStatus.PENDING,
        )

    def tearDown(self):
        cache.clear()

    def test_public_review_list_shows_only_approved_reviews(self):
        """Public reviews list must only display APPROVED reviews."""
        response = self.client.get(f"/api/v1/catalog/products/{self.product.slug}/reviews/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        results = data["data"]["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], str(self.approved_review.id))
        self.assertEqual(results[0]["title"], "Incomparable aroma")
        # Reviewer name must be masked (Firstname L.)
        self.assertEqual(results[0]["reviewer_name"], "Anand H.")

    def test_submit_review_unauthenticated_fails(self):
        """Unauthenticated review submissions must be rejected with 401."""
        response = self.client.post(
            f"/api/v1/catalog/products/{self.product.slug}/reviews/",
            data={"rating": 5, "title": "Great", "review_body": "Loved it"},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_submit_review_rating_validation(self):
        """Ratings must be between 1 and 5 stars."""
        new_shopper = User.objects.create_user(
            email="shopper3@example.com",
            phone_number="+919700000004",
            password="SecurePassword123!",
        )
        self.client.force_authenticate(user=new_shopper)

        # Rating 0 (invalid)
        resp_zero = self.client.post(
            f"/api/v1/catalog/products/{self.product.slug}/reviews/",
            data={"rating": 0, "title": "Zero", "review_body": "Bad rating"},
        )
        self.assertEqual(resp_zero.status_code, status.HTTP_400_BAD_REQUEST)

        # Rating 6 (invalid)
        resp_six = self.client.post(
            f"/api/v1/catalog/products/{self.product.slug}/reviews/",
            data={"rating": 6, "title": "Six", "review_body": "Too high"},
        )
        self.assertEqual(resp_six.status_code, status.HTTP_400_BAD_REQUEST)

    def test_submit_review_anti_spoofing_and_pending_moderation(self):
        """
        User submitting review cannot spoof verified_purchase or moderation_status.
        Review is created with status PENDING.
        """
        new_shopper = User.objects.create_user(
            email="shopper4@example.com",
            phone_number="+919700000005",
            password="SecurePassword123!",
            first_name="Mahesh",
            last_name="Bhat",
        )
        self.client.force_authenticate(user=new_shopper)

        payload = {
            "rating": 5,
            "title": "Unbelievable freshness",
            "review_body": "Grown in Malenadu stamp is completely authentic.",
            "verified_purchase": True,  # Attempting to spoof
            "moderation_status": "APPROVED",  # Attempting to bypass moderation
        }
        response = self.client.post(
            f"/api/v1/catalog/products/{self.product.slug}/reviews/",
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()["data"]
        self.assertEqual(data["moderation_status"], "PENDING")
        self.assertFalse(data["verified_purchase"])

        # Check in DB
        created_review = ProductReview.objects.get(id=data["id"])
        self.assertEqual(created_review.moderation_status, ModerationStatus.PENDING)
        self.assertFalse(created_review.verified_purchase)

    def test_submit_review_verified_purchase_true_when_order_delivered(self):
        """
        When an authenticated user has a DELIVERED order containing the product,
        submitting a review sets verified_purchase=True automatically.
        """
        buyer = User.objects.create_user(
            email="verified_buyer@example.com",
            phone_number="+919700000099",
            password="SecurePassword123!",
            first_name="Ramesh",
            last_name="Bhat",
        )
        # Create delivered order
        order = Order.objects.create(
            order_number="BMP-ORD-VERIF-101",
            user=buyer,
            order_status=OrderStatus.DELIVERED,
            shipping_recipient_name="Ramesh Bhat",
            shipping_phone_number="+919700000099",
            shipping_address_line_1="Car Street",
            shipping_city="Mangalore",
            shipping_state="Karnataka",
            shipping_pincode="575001",
            items_subtotal=Decimal("350.00"),
            grand_total=Decimal("350.00"),
        )
        OrderLineItem.objects.create(
            order=order,
            variant=self.variant,
            product_name="Sirsi Bold Black Pepper",
            variant_name="250g",
            sku="PEPPER-250G",
            weight_in_grams=250,
            quantity=1,
            mrp=Decimal("350.00"),
            unit_price=Decimal("350.00"),
            line_subtotal=Decimal("350.00"),
        )

        self.client.force_authenticate(user=buyer)
        payload = {
            "rating": 5,
            "title": "Authentic aroma",
            "review_body": "Delivered promptly, exceptional spice freshness.",
        }
        response = self.client.post(
            f"/api/v1/catalog/products/{self.product.slug}/reviews/",
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()["data"]
        self.assertTrue(data["verified_purchase"])

        created_review = ProductReview.objects.get(id=data["id"])
        self.assertTrue(created_review.verified_purchase)

    def test_duplicate_review_by_same_user_is_rejected(self):
        """A user cannot submit multiple reviews for the same product."""
        self.client.force_authenticate(user=self.reviewer1)
        response = self.client.post(
            f"/api/v1/catalog/products/{self.product.slug}/reviews/",
            data={"rating": 4, "title": "Second Review", "review_body": "Duplicate attempt"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_staff_review_moderation_workflow(self):
        """
        Operations staff can approve or reject reviews.
        Approved reviews immediately appear in the public catalog.
        """
        # 1. Retail user attempting to moderate -> 403 Forbidden
        self.client.force_authenticate(user=self.reviewer1)
        resp_forbidden = self.client.post(
            f"/api/v1/staff/catalog/reviews/{self.pending_review.id}/moderate/",
            data={"action": "APPROVE"},
        )
        self.assertEqual(resp_forbidden.status_code, status.HTTP_403_FORBIDDEN)

        # 2. Staff user approves review -> 200 OK
        self.client.force_authenticate(user=self.staff_user)
        resp_approve = self.client.post(
            f"/api/v1/staff/catalog/reviews/{self.pending_review.id}/moderate/",
            data={"action": "APPROVE"},
        )
        self.assertEqual(resp_approve.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_approve.json()["data"]["moderation_status"], "APPROVED")

        self.pending_review.refresh_from_db()
        self.assertEqual(self.pending_review.moderation_status, ModerationStatus.APPROVED)

        # 3. Verify it now appears in public reviews API
        self.client.logout()
        resp_public = self.client.get(f"/api/v1/catalog/products/{self.product.slug}/reviews/")
        self.assertEqual(resp_public.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_public.json()["data"]["count"], 2)

    def test_staff_review_moderation_reject_workflow(self):
        """Operations staff rejects review -> status becomes REJECTED."""
        self.client.force_authenticate(user=self.staff_user)
        resp_reject = self.client.post(
            f"/api/v1/staff/catalog/reviews/{self.pending_review.id}/moderate/",
            data={"action": "REJECT"},
        )
        self.assertEqual(resp_reject.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_reject.json()["data"]["moderation_status"], "REJECTED")

        self.pending_review.refresh_from_db()
        self.assertEqual(self.pending_review.moderation_status, ModerationStatus.REJECTED)
