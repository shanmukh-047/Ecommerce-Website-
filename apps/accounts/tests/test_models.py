import uuid

from django.db import IntegrityError
from django.test import TestCase

from apps.accounts.models import (
    Address,
    IndianStates,
    Role,
    User,
)


class UserModelTests(TestCase):
    def test_create_retail_user_successful(self):
        user = User.objects.create_user(
            email="CUSTOMER@BharathMasala.com",
            phone_number="9876543210",
            password="SecurePassword123!",
            first_name="Sharada",
            last_name="Hegde",
        )
        self.assertIsInstance(user.id, uuid.UUID)
        self.assertEqual(user.email, "customer@bharathmasala.com")
        self.assertEqual(user.phone_number, "+919876543210")
        self.assertEqual(user.role, Role.CUSTOMER)
        self.assertTrue(user.check_password("SecurePassword123!"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_wholesale_buyer)

    def test_duplicate_email_raises_error(self):
        User.objects.create_user(
            email="duplicate@bharathmasala.com",
            phone_number="9876543210",
            password="Password123!",
        )
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                email="DUPLICATE@bharathmasala.com",
                phone_number="9876543211",
                password="Password123!",
            )

    def test_duplicate_phone_raises_error(self):
        User.objects.create_user(
            email="user1@bharathmasala.com",
            phone_number="9876543210",
            password="Password123!",
        )
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                email="user2@bharathmasala.com",
                phone_number="+91 98765 43210",  # Normalizes to same phone
                password="Password123!",
            )

    def test_create_superuser(self):
        admin_user = User.objects.create_superuser(
            email="admin@bharathmasala.com",
            phone_number="9876543299",
            password="SuperAdminPassword123!",
        )
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        self.assertEqual(admin_user.role, Role.SUPERADMIN)


class AddressModelTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            email="user1@test.com", phone_number="9876500001", password="Password123!"
        )
        self.user2 = User.objects.create_user(
            email="user2@test.com", phone_number="9876500002", password="Password123!"
        )

    def test_single_default_shipping_address_enforced(self):
        addr1 = Address.objects.create(
            user=self.user1,
            recipient_name="User 1 Recipient",
            phone_number="9876500001",
            address_line_1="Estate Road 1",
            city="Sirsi",
            state=IndianStates.KARNATAKA,
            pincode="581401",
            is_default_shipping=True,
        )
        self.assertTrue(addr1.is_default_shipping)

        addr2 = Address.objects.create(
            user=self.user1,
            recipient_name="User 1 Recipient Second",
            phone_number="9876500001",
            address_line_1="Market Road 2",
            city="Sirsi",
            state=IndianStates.KARNATAKA,
            pincode="581401",
            is_default_shipping=True,
        )

        addr1.refresh_from_db()
        addr2.refresh_from_db()

        self.assertFalse(addr1.is_default_shipping)
        self.assertTrue(addr2.is_default_shipping)

    def test_default_shipping_isolation_across_users(self):
        addr_u1 = Address.objects.create(
            user=self.user1,
            recipient_name="User 1",
            phone_number="9876500001",
            address_line_1="Address 1",
            city="Sirsi",
            state=IndianStates.KARNATAKA,
            pincode="581401",
            is_default_shipping=True,
        )
        addr_u2 = Address.objects.create(
            user=self.user2,
            recipient_name="User 2",
            phone_number="9876500002",
            address_line_1="Address 2",
            city="Bengaluru",
            state=IndianStates.KARNATAKA,
            pincode="560001",
            is_default_shipping=True,
        )
        addr_u1.refresh_from_db()
        addr_u2.refresh_from_db()

        self.assertTrue(addr_u1.is_default_shipping)
        self.assertTrue(addr_u2.is_default_shipping)
