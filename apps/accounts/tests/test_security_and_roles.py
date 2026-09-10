import logging

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Role, User, VerificationStatus, WholesaleProfile
from apps.accounts.permissions import IsApprovedWholesaleBuyer, IsManagerOrAdmin, IsStaffOrManager
from apps.core.middleware import PIIMaskingFilter


class SecurityAndRoleTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_permission_classes_logic(self):
        # Setup users for each role
        customer = User.objects.create_user(
            email="cust@test.com",
            phone_number="9876580001",
            password="Password123!",
            role=Role.CUSTOMER,
        )
        wholesale_pending = User.objects.create_user(
            email="pending@test.com",
            phone_number="9876580002",
            password="Password123!",
            role=Role.WHOLESALE_PENDING,
        )
        wholesale_approved = User.objects.create_user(
            email="approved@test.com",
            phone_number="9876580003",
            password="Password123!",
            role=Role.WHOLESALE_APPROVED,
        )
        WholesaleProfile.objects.create(
            user=wholesale_approved,
            company_name="Approved Foods",
            gstin="29ABCDE1234F1Z5",
            pan_number="ABCDE1234F",
            verification_status=VerificationStatus.APPROVED,
        )

        staff_user = User.objects.create_user(
            email="staff@test.com",
            phone_number="9876580004",
            password="Password123!",
            role=Role.STAFF,
        )
        manager_user = User.objects.create_user(
            email="mgr@test.com",
            phone_number="9876580005",
            password="Password123!",
            role=Role.MANAGER,
        )
        superadmin_user = User.objects.create_superuser(
            email="super@test.com", phone_number="9876580006", password="Password123!"
        )

        class DummyRequest:
            def __init__(self, user):
                self.user = user

        # Test IsApprovedWholesaleBuyer
        perm_wholesale = IsApprovedWholesaleBuyer()
        self.assertFalse(perm_wholesale.has_permission(DummyRequest(customer), None))
        self.assertFalse(perm_wholesale.has_permission(DummyRequest(wholesale_pending), None))
        self.assertTrue(perm_wholesale.has_permission(DummyRequest(wholesale_approved), None))
        self.assertFalse(perm_wholesale.has_permission(DummyRequest(staff_user), None))

        # Test IsStaffOrManager
        perm_staff = IsStaffOrManager()
        self.assertFalse(perm_staff.has_permission(DummyRequest(customer), None))
        self.assertTrue(perm_staff.has_permission(DummyRequest(staff_user), None))
        self.assertTrue(perm_staff.has_permission(DummyRequest(manager_user), None))
        self.assertTrue(perm_staff.has_permission(DummyRequest(superadmin_user), None))

        # Test IsManagerOrAdmin
        perm_mgr = IsManagerOrAdmin()
        self.assertFalse(perm_mgr.has_permission(DummyRequest(customer), None))
        self.assertFalse(perm_mgr.has_permission(DummyRequest(staff_user), None))
        self.assertTrue(perm_mgr.has_permission(DummyRequest(manager_user), None))
        self.assertTrue(perm_mgr.has_permission(DummyRequest(superadmin_user), None))

    def test_sensitive_kyc_data_masking_in_api(self):
        """Wholesale profile read responses must mask full PAN and GSTIN."""
        user = User.objects.create_user(
            email="kyc@test.com",
            phone_number="9876580010",
            password="Password123!",
            role=Role.WHOLESALE_APPROVED,
        )
        WholesaleProfile.objects.create(
            user=user,
            company_name="Spice Traders Ltd",
            gstin="29ABCDE1234F1Z5",
            pan_number="ABCDE1234F",
            verification_status=VerificationStatus.APPROVED,
        )
        self.client.force_authenticate(user=user)
        res = self.client.get(reverse("auth:me"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()["data"]["wholesale_profile"]

        # Ensure masked fields are exposed, NOT raw fields
        self.assertEqual(data["masked_gstin"], "29ABCDE****F1Z5")
        self.assertEqual(data["masked_pan"], "ABCDE****F")
        self.assertNotIn("pan_number", data)
        self.assertNotIn("gstin", data)

    def test_pii_masking_log_filter(self):
        """PIIMaskingFilter must scrub PAN, GSTIN, and passwords from log records."""
        filter_instance = PIIMaskingFilter()
        log_record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg="User registered with pan ABCDE1234F and gstin 29ABCDE1234F1Z5 and password: 'SecretPassword!'",
            args=(),
            exc_info=None,
        )
        filter_instance.filter(log_record)

        self.assertNotIn("ABCDE1234F", log_record.msg)
        self.assertNotIn("29ABCDE1234F1Z5", log_record.msg)
        self.assertNotIn("SecretPassword!", log_record.msg)
        self.assertIn("ABCD****F", log_record.msg)
        self.assertIn("29ABC******Z5", log_record.msg)

    def test_rate_limiting_on_auth_endpoint(self):
        """Auth endpoints must throttle excessive consecutive attempts (5/min)."""
        login_url = reverse("auth:login")
        # Send 6 rapid requests
        status_codes = []
        for i in range(6):
            res = self.client.post(
                login_url,
                {"email": f"test{i}@test.com", "password": "WrongPassword!"},
                format="json",
            )
            status_codes.append(res.status_code)

        # At least the 6th request must be throttled with HTTP 429
        self.assertIn(status.HTTP_429_TOO_MANY_REQUESTS, status_codes)
