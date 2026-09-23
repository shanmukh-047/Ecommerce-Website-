import os
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.accounts.models import Role, User


class BootstrapAdminCommandTests(TestCase):
    """
    Test suite for the safe one-time production admin bootstrap management command.
    Verifies strict gate validation, credential handling, role assignment, and zero password leakage.
    """

    def setUp(self):
        self.valid_password = "SuperSecureAdminPass987!"
        self.admin_email = "prodadmin@bharathmasala.com"
        self.admin_phone = "+919876543210"

    def test_refuses_to_run_when_bootstrap_flag_is_not_set(self):
        out = StringIO()
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(CommandError) as ctx:
                call_command("bootstrap_admin", stdout=out, stderr=out)

            self.assertIn("BOOTSTRAP_ADMIN environment variable must be explicitly set to 'true'", str(ctx.exception))
            self.assertEqual(User.objects.count(), 0)

    def test_refuses_to_run_when_bootstrap_flag_is_false(self):
        out = StringIO()
        with patch.dict(os.environ, {"BOOTSTRAP_ADMIN": "false"}, clear=True):
            with self.assertRaises(CommandError) as ctx:
                call_command("bootstrap_admin", stdout=out, stderr=out)

            self.assertIn("BOOTSTRAP_ADMIN environment variable must be explicitly set to 'true'", str(ctx.exception))
            self.assertEqual(User.objects.count(), 0)

    def test_refuses_to_run_when_email_missing(self):
        out = StringIO()
        env = {
            "BOOTSTRAP_ADMIN": "true",
            "ADMIN_PASSWORD": self.valid_password,
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(CommandError) as ctx:
                call_command("bootstrap_admin", stdout=out, stderr=out)

            self.assertIn("ADMIN_EMAIL environment variable is required", str(ctx.exception))

    def test_refuses_to_run_when_email_invalid(self):
        out = StringIO()
        env = {
            "BOOTSTRAP_ADMIN": "true",
            "ADMIN_EMAIL": "invalid-email-address",
            "ADMIN_PASSWORD": self.valid_password,
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(CommandError) as ctx:
                call_command("bootstrap_admin", stdout=out, stderr=out)

            self.assertIn("is not a valid email address", str(ctx.exception))

    def test_refuses_to_run_when_password_missing(self):
        out = StringIO()
        env = {
            "BOOTSTRAP_ADMIN": "true",
            "ADMIN_EMAIL": self.admin_email,
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(CommandError) as ctx:
                call_command("bootstrap_admin", stdout=out, stderr=out)

            self.assertIn("ADMIN_PASSWORD environment variable is required", str(ctx.exception))

    def test_refuses_to_run_when_password_too_weak(self):
        out = StringIO()
        env = {
            "BOOTSTRAP_ADMIN": "true",
            "ADMIN_EMAIL": self.admin_email,
            "ADMIN_PASSWORD": "123",  # Fails minimum length and common password validation
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(CommandError) as ctx:
                call_command("bootstrap_admin", stdout=out, stderr=out)

            self.assertIn("ADMIN_PASSWORD does not meet security requirements", str(ctx.exception))
            # Verify plaintext password was NOT echoed in error
            self.assertNotIn("123", str(ctx.exception))

    def test_successfully_creates_new_superuser(self):
        out = StringIO()
        env = {
            "BOOTSTRAP_ADMIN": "true",
            "ADMIN_EMAIL": self.admin_email,
            "ADMIN_PASSWORD": self.valid_password,
            "ADMIN_PHONE": self.admin_phone,
            "ADMIN_FIRST_NAME": "Lead",
            "ADMIN_LAST_NAME": "Administrator",
        }
        with patch.dict(os.environ, env, clear=True):
            call_command("bootstrap_admin", stdout=out)

        output_text = out.getvalue()
        self.assertIn("ADMIN BOOTSTRAP COMPLETE", output_text)
        self.assertIn("Created new Super Administrator account", output_text)
        self.assertIn(self.admin_email, output_text)
        # Verify plaintext password is NEVER leaked in output
        self.assertNotIn(self.valid_password, output_text)

        # Verify database state
        user = User.objects.get(email=self.admin_email)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertEqual(user.role, Role.SUPERADMIN)
        self.assertEqual(user.first_name, "Lead")
        self.assertEqual(user.last_name, "Administrator")
        self.assertTrue(user.check_password(self.valid_password))

    def test_successfully_updates_existing_user_to_superuser(self):
        # Create regular customer first
        existing_user = User.objects.create_user(
            email=self.admin_email,
            phone_number=self.admin_phone,
            password="OldCustomerPassword123!",
            role=Role.CUSTOMER,
            first_name="Regular",
            last_name="Customer",
        )
        self.assertFalse(existing_user.is_staff)
        self.assertFalse(existing_user.is_superuser)
        self.assertEqual(existing_user.role, Role.CUSTOMER)

        out = StringIO()
        env = {
            "BOOTSTRAP_ADMIN": "true",
            "ADMIN_EMAIL": self.admin_email,
            "ADMIN_PASSWORD": self.valid_password,
        }
        with patch.dict(os.environ, env, clear=True):
            call_command("bootstrap_admin", stdout=out)

        output_text = out.getvalue()
        self.assertIn("Updated existing user to Super Administrator and reset password", output_text)
        self.assertNotIn(self.valid_password, output_text)

        # Verify upgraded user
        existing_user.refresh_from_db()
        self.assertTrue(existing_user.is_staff)
        self.assertTrue(existing_user.is_superuser)
        self.assertEqual(existing_user.role, Role.SUPERADMIN)
        self.assertTrue(existing_user.check_password(self.valid_password))
        self.assertFalse(existing_user.check_password("OldCustomerPassword123!"))

    def test_phone_number_conflict_handling_with_alternate_fallback(self):
        # Existing user with the phone number
        User.objects.create_user(
            email="someoneelse@test.com",
            phone_number="+919876543210",
            password="Password123!",
        )

        out = StringIO()
        env = {
            "BOOTSTRAP_ADMIN": "true",
            "ADMIN_EMAIL": "brandnewadmin@bharathmasala.com",
            "ADMIN_PASSWORD": self.valid_password,
            # No ADMIN_PHONE provided, default +919876543210 is taken
        }
        with patch.dict(os.environ, env, clear=True):
            call_command("bootstrap_admin", stdout=out)

        # Should have fallen back to secondary admin phone +919999999999
        admin_user = User.objects.get(email="brandnewadmin@bharathmasala.com")
        self.assertEqual(admin_user.phone_number, "+919999999999")
        self.assertTrue(admin_user.is_superuser)
