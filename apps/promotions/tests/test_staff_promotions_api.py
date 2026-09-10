from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.promotions.models import Coupon, DiscountType


class StaffPromotionAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.now = timezone.now()

        self.customer = User.objects.create_user(
            "cust@example.com", "9876543251", "StrongPassword123!"
        )
        self.staff_user = User.objects.create_user(
            "staff_promo@bharathmasala.com", "9876543252", "StrongPassword123!", role=Role.STAFF
        )
        self.staff_user.is_staff = True
        self.staff_user.save()

        self.manager_user = User.objects.create_user(
            "manager_promo@bharathmasala.com", "9876543253", "StrongPassword123!", role=Role.MANAGER
        )
        self.manager_user.is_staff = True
        self.manager_user.save()

        self.coupon = Coupon.objects.create(
            code="STAFFTEST",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal("15.00"),
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=7),
        )

    def test_anonymous_access_denied(self):
        url = reverse("staff-coupon-list-create")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_customer_access_forbidden(self):
        self.client.force_authenticate(user=self.customer)
        url = reverse("staff-coupon-list-create")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_can_list_coupons(self):
        self.client.force_authenticate(user=self.staff_user)
        url = reverse("staff-coupon-list-create")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_staff_cannot_create_coupons(self):
        self.client.force_authenticate(user=self.staff_user)
        url = reverse("staff-coupon-list-create")
        payload = {
            "code": "NEWCODE20",
            "discount_type": "PERCENTAGE",
            "discount_value": "20.00",
            "valid_from": self.now.isoformat(),
            "valid_to": (self.now + timedelta(days=5)).isoformat(),
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_create_coupon(self):
        self.client.force_authenticate(user=self.manager_user)
        url = reverse("staff-coupon-list-create")
        payload = {
            "code": "MGRCODE20",
            "discount_type": "PERCENTAGE",
            "discount_value": "20.00",
            "valid_from": self.now.isoformat(),
            "valid_to": (self.now + timedelta(days=5)).isoformat(),
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Coupon.objects.filter(code="MGRCODE20").count(), 1)

    def test_manager_can_toggle_coupon(self):
        self.client.force_authenticate(user=self.manager_user)
        url = reverse("staff-coupon-toggle", kwargs={"pk": self.coupon.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.coupon.refresh_from_db()
        self.assertFalse(self.coupon.is_active)
