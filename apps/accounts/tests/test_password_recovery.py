from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.core.cache import cache
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


class PasswordRecoveryAndChangeTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.customer = User.objects.create_user(
            email="recovery_cust@example.com",
            phone_number="9876540001",
            password="OldPassword@123",
            first_name="Recovery",
            last_name="Tester",
            role="CUSTOMER",
        )
        self.staff_user = User.objects.create_user(
            email="staff_recovery@bharathmasala.com",
            phone_number="9876540002",
            password="StaffOldPass@123",
            first_name="Staff",
            last_name="Member",
            role="STAFF",
            is_staff=True,
        )

        self.reset_request_url = reverse("auth:password-reset")
        self.reset_confirm_url = reverse("auth:password-reset-confirm")
        self.change_password_url = reverse("auth:change-password")
        self.login_url = reverse("auth:login")

    def tearDown(self):
        cache.clear()

    def test_forgot_password_for_existing_customer(self):
        """Requesting password reset for registered email sends reset link."""
        mail.outbox = []
        res = self.client.post(self.reset_request_url, {"email": "recovery_cust@example.com"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("instructions", res.json().get("message", "").lower())

        # Verify email was dispatched to outbox
        self.assertEqual(len(mail.outbox), 1)
        sent_mail = mail.outbox[0]
        self.assertIn("recovery_cust@example.com", sent_mail.to)
        self.assertIn("Reset Your Bharat Masala Password", sent_mail.subject)
        self.assertIn("/reset-password?uid=", sent_mail.body)
        self.assertNotIn("OldPassword@123", sent_mail.body)

    def test_forgot_password_enumeration_protection(self):
        """Requesting password reset for non-existent email returns generic 200 without sending email."""
        mail.outbox = []
        res = self.client.post(self.reset_request_url, {"email": "non_existent_999@example.com"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Email outbox remains empty
        self.assertEqual(len(mail.outbox), 0)
        self.assertIn("instructions", res.json().get("message", "").lower())

    def test_successful_password_reset_flow(self):
        """Full reset flow: request -> token -> confirm -> login with new password."""
        uidb64 = urlsafe_base64_encode(force_bytes(self.customer.pk))
        token = default_token_generator.make_token(self.customer)

        res = self.client.post(
            self.reset_confirm_url,
            {
                "uid": uidb64,
                "token": token,
                "new_password": "NewSecurePassword@456",
                "confirm_password": "NewSecurePassword@456",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Login with old password fails
        res_old = self.client.post(
            self.login_url,
            {"email": "recovery_cust@example.com", "password": "OldPassword@123"},
            format="json",
        )
        self.assertEqual(res_old.status_code, status.HTTP_400_BAD_REQUEST)

        # Login with new password succeeds
        res_new = self.client.post(
            self.login_url,
            {"email": "recovery_cust@example.com", "password": "NewSecurePassword@456"},
            format="json",
        )
        self.assertEqual(res_new.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", res_new.json().get("data", {}))

    def test_token_reuse_fails(self):
        """A reset token cannot be reused once the password is changed."""
        uidb64 = urlsafe_base64_encode(force_bytes(self.customer.pk))
        token = default_token_generator.make_token(self.customer)

        # First reset succeeds
        res1 = self.client.post(
            self.reset_confirm_url,
            {
                "uid": uidb64,
                "token": token,
                "new_password": "NewSecurePassword@456",
                "confirm_password": "NewSecurePassword@456",
            },
            format="json",
        )
        self.assertEqual(res1.status_code, status.HTTP_200_OK)

        # Reusing the exact same token must fail
        res2 = self.client.post(
            self.reset_confirm_url,
            {
                "uid": uidb64,
                "token": token,
                "new_password": "AnotherPassword@789",
                "confirm_password": "AnotherPassword@789",
            },
            format="json",
        )
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_reset_token_fails(self):
        """Submitting an altered/tampered token fails."""
        uidb64 = urlsafe_base64_encode(force_bytes(self.customer.pk))
        res = self.client.post(
            self.reset_confirm_url,
            {
                "uid": uidb64,
                "token": "invalid-tampered-token-123",
                "new_password": "NewSecurePassword@456",
                "confirm_password": "NewSecurePassword@456",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_reset_password_mismatch(self):
        """Passwords mismatch in reset confirm fails validation."""
        uidb64 = urlsafe_base64_encode(force_bytes(self.customer.pk))
        token = default_token_generator.make_token(self.customer)

        res = self.client.post(
            self.reset_confirm_url,
            {
                "uid": uidb64,
                "token": token,
                "new_password": "NewSecurePassword@456",
                "confirm_password": "DifferentPassword@789",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_weak_password_in_reset_fails(self):
        """Submitting a password that violates standard validators (e.g. too short) fails."""
        uidb64 = urlsafe_base64_encode(force_bytes(self.customer.pk))
        token = default_token_generator.make_token(self.customer)

        res = self.client.post(
            self.reset_confirm_url,
            {
                "uid": uidb64,
                "token": token,
                "new_password": "short",
                "confirm_password": "short",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_authenticated_change_password_success(self):
        """Logged-in customer can change password by providing correct current password."""
        self.client.force_authenticate(user=self.customer)

        res = self.client.post(
            self.change_password_url,
            {
                "current_password": "OldPassword@123",
                "new_password": "UpdatedPassword@999",
                "confirm_password": "UpdatedPassword@999",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Login with new password works
        self.client.logout()
        res_login = self.client.post(
            self.login_url,
            {"email": "recovery_cust@example.com", "password": "UpdatedPassword@999"},
            format="json",
        )
        self.assertEqual(res_login.status_code, status.HTTP_200_OK)

    def test_change_password_wrong_current_password(self):
        """Providing incorrect current password rejects change."""
        self.client.force_authenticate(user=self.customer)

        res = self.client.post(
            self.change_password_url,
            {
                "current_password": "IncorrectOldPassword!",
                "new_password": "UpdatedPassword@999",
                "confirm_password": "UpdatedPassword@999",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_same_as_current(self):
        """Setting new password identical to current password is rejected."""
        self.client.force_authenticate(user=self.customer)

        res = self.client.post(
            self.change_password_url,
            {
                "current_password": "OldPassword@123",
                "new_password": "OldPassword@123",
                "confirm_password": "OldPassword@123",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_change_password_denied(self):
        """Unauthenticated requests to change-password return 401."""
        res = self.client.post(
            self.change_password_url,
            {
                "current_password": "OldPassword@123",
                "new_password": "UpdatedPassword@999",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_staff_forgot_and_reset_password(self):
        """Staff members can use the secure recovery system."""
        mail.outbox = []
        res = self.client.post(self.reset_request_url, {"email": "staff_recovery@bharathmasala.com"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)

        # Reset staff password
        uidb64 = urlsafe_base64_encode(force_bytes(self.staff_user.pk))
        token = default_token_generator.make_token(self.staff_user)

        res_reset = self.client.post(
            self.reset_confirm_url,
            {
                "uid": uidb64,
                "token": token,
                "new_password": "StaffNewSecurePass@999",
                "confirm_password": "StaffNewSecurePass@999",
            },
            format="json",
        )
        self.assertEqual(res_reset.status_code, status.HTTP_200_OK)

        # Staff can log in with new password
        res_login = self.client.post(
            self.login_url,
            {"email": "staff_recovery@bharathmasala.com", "password": "StaffNewSecurePass@999"},
            format="json",
        )
        self.assertEqual(res_login.status_code, status.HTTP_200_OK)
        self.assertTrue(res_login.json()["data"]["user"]["is_staff"])
