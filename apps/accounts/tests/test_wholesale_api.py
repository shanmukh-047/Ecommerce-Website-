from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import BusinessType, Role, User, VerificationStatus, WholesaleProfile


class WholesaleAPITests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.register_wholesale_url = reverse("auth:register-wholesale")

        # Create manager and customer users
        self.manager = User.objects.create_user(
            email="manager@bharathmasala.com",
            phone_number="9876599991",
            password="ManagerPassword123!",
            role=Role.MANAGER,
            first_name="Operations",
            last_name="Manager",
        )
        self.customer = User.objects.create_user(
            email="regular@bharathmasala.com",
            phone_number="9876599992",
            password="CustomerPassword123!",
            role=Role.CUSTOMER,
        )

    def tearDown(self):
        cache.clear()

    def test_wholesale_registration_success(self):
        payload = {
            "user": {
                "email": "hotel@udupi.com",
                "phone_number": "9876501234",
                "password": "SecurePassword123!",
                "confirm_password": "SecurePassword123!",
                "first_name": "Ramesh",
                "last_name": "Bhat",
            },
            "company_name": "Udupi Grand Hotel & Kitchens",
            "gstin": "29ABCDE1234F1Z5",
            "pan_number": "ABCDE1234F",
            "fssai_license": "11223344556677",
            "business_type": BusinessType.HORECA,
        }
        res = self.client.post(self.register_wholesale_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        user = User.objects.get(email="hotel@udupi.com")
        self.assertEqual(user.role, Role.WHOLESALE_PENDING)
        self.assertFalse(user.is_wholesale_buyer)

        profile = WholesaleProfile.objects.get(user=user)
        self.assertEqual(profile.company_name, "Udupi Grand Hotel & Kitchens")
        self.assertEqual(profile.verification_status, VerificationStatus.PENDING)
        self.assertEqual(profile.business_type, BusinessType.HORECA)

    def test_wholesale_registration_invalid_gstin(self):
        payload = {
            "user": {
                "email": "badgst@udupi.com",
                "phone_number": "9876501235",
                "password": "SecurePassword123!",
                "confirm_password": "SecurePassword123!",
            },
            "company_name": "Bad GST Store",
            "gstin": "INVALID123",
            "pan_number": "ABCDE1234F",
            "business_type": BusinessType.RETAILER,
        }
        res = self.client.post(self.register_wholesale_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("gstin", res.json()["error"]["details"])
        self.assertFalse(User.objects.filter(email="badgst@udupi.com").exists())

    def test_manager_approves_wholesale_profile(self):
        # Register wholesale applicant
        user = User.objects.create_user(
            email="wholesale1@buyer.com",
            phone_number="9876501236",
            password="Password123!",
            role=Role.WHOLESALE_PENDING,
        )
        profile = WholesaleProfile.objects.create(
            user=user,
            company_name="Malenadu Grocers",
            gstin="29ABCDE1234F1Z5",
            pan_number="ABCDE1234F",
            business_type=BusinessType.RETAILER,
        )

        verify_url = reverse("staff:wholesale-verify", kwargs={"pk": profile.pk})

        # Regular customer cannot verify (403 Forbidden)
        self.client.force_authenticate(user=self.customer)
        unauth_res = self.client.post(verify_url, {"action": "APPROVE"}, format="json")
        self.assertEqual(unauth_res.status_code, status.HTTP_403_FORBIDDEN)

        # Manager approves
        self.client.force_authenticate(user=self.manager)
        approve_res = self.client.post(verify_url, {"action": "APPROVE"}, format="json")
        self.assertEqual(approve_res.status_code, status.HTTP_200_OK)

        profile.refresh_from_db()
        user.refresh_from_db()

        self.assertEqual(profile.verification_status, VerificationStatus.APPROVED)
        self.assertEqual(profile.verified_by, self.manager)
        self.assertIsNotNone(profile.verified_at)
        self.assertEqual(user.role, Role.WHOLESALE_APPROVED)
        self.assertTrue(user.is_wholesale_buyer)

    def test_manager_rejects_wholesale_profile(self):
        user = User.objects.create_user(
            email="wholesale2@buyer.com",
            phone_number="9876501237",
            password="Password123!",
            role=Role.WHOLESALE_PENDING,
        )
        profile = WholesaleProfile.objects.create(
            user=user,
            company_name="Fake Spices LLC",
            gstin="29ABCDE1234F1Z5",
            pan_number="ABCDE1234F",
            business_type=BusinessType.RETAILER,
        )

        verify_url = reverse("staff:wholesale-verify", kwargs={"pk": profile.pk})
        self.client.force_authenticate(user=self.manager)

        # Rejection without reason fails
        fail_res = self.client.post(verify_url, {"action": "REJECT"}, format="json")
        self.assertEqual(fail_res.status_code, status.HTTP_400_BAD_REQUEST)

        # Rejection with reason succeeds
        reject_res = self.client.post(
            verify_url,
            {
                "action": "REJECT",
                "rejection_reason": "GSTIN registration cancelled in state records.",
            },
            format="json",
        )
        self.assertEqual(reject_res.status_code, status.HTTP_200_OK)

        profile.refresh_from_db()
        user.refresh_from_db()

        self.assertEqual(profile.verification_status, VerificationStatus.REJECTED)
        self.assertEqual(profile.rejection_reason, "GSTIN registration cancelled in state records.")
        self.assertEqual(user.role, Role.WHOLESALE_PENDING)
        self.assertFalse(user.is_wholesale_buyer)
