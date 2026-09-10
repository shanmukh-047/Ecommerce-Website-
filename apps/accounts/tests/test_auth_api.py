from django.conf import settings
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Role, User


class AuthAPITests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.register_url = reverse("auth:register")
        self.login_url = reverse("auth:login")
        self.refresh_url = reverse("auth:token-refresh")
        self.logout_url = reverse("auth:logout")
        self.me_url = reverse("auth:me")

    def tearDown(self):
        cache.clear()

    def test_customer_registration_success(self):
        payload = {
            "email": "sharada@malenadu.in",
            "phone_number": "9876543210",
            "first_name": "Sharada",
            "last_name": "Bhat",
            "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!",
        }
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("access_token", data["data"])
        self.assertEqual(data["data"]["user"]["role"], Role.CUSTOMER)
        self.assertEqual(data["data"]["user"]["email"], "sharada@malenadu.in")

        # Verify HttpOnly refresh cookie is set
        cookie_name = getattr(settings, "JWT_REFRESH_COOKIE_NAME", "refresh_token")
        self.assertIn(cookie_name, response.cookies)
        cookie = response.cookies[cookie_name]
        self.assertTrue(cookie["httponly"])

    def test_customer_registration_rejects_client_role_injection(self):
        """Privilege escalation check: user cannot grant themselves superadmin or manager role."""
        payload = {
            "email": "hacker@malenadu.in",
            "phone_number": "9876543211",
            "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!",
            "role": "SUPERADMIN",
            "is_staff": True,
            "is_superuser": True,
        }
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="hacker@malenadu.in")
        self.assertEqual(user.role, Role.CUSTOMER)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_customer_registration_password_mismatch(self):
        payload = {
            "email": "mismatch@malenadu.in",
            "phone_number": "9876543212",
            "password": "StrongPassword123!",
            "confirm_password": "DifferentPassword123!",
        }
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "VALIDATION_ERROR")

    def test_login_success(self):
        User.objects.create_user(
            email="login@malenadu.in",
            phone_number="9876543213",
            password="LoginPassword123!",
        )
        response = self.client.post(
            self.login_url,
            {"email": "login@malenadu.in", "password": "LoginPassword123!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("access_token", data["data"])

    def test_login_invalid_password(self):
        User.objects.create_user(
            email="login2@malenadu.in",
            phone_number="9876543214",
            password="LoginPassword123!",
        )
        response = self.client.post(
            self.login_url,
            {"email": "login2@malenadu.in", "password": "WrongPassword!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["message"], "Invalid email or password.")

    def test_token_refresh_and_rotation(self):
        User.objects.create_user(
            email="refresh@malenadu.in",
            phone_number="9876543215",
            password="Password123!",
        )
        login_res = self.client.post(
            self.login_url,
            {"email": "refresh@malenadu.in", "password": "Password123!"},
            format="json",
        )
        cookie_name = getattr(settings, "JWT_REFRESH_COOKIE_NAME", "refresh_token")
        initial_refresh = login_res.cookies[cookie_name].value

        # Call refresh endpoint with cookie
        self.client.cookies[cookie_name] = initial_refresh
        refresh_res = self.client.post(self.refresh_url, {}, format="json")
        self.assertEqual(refresh_res.status_code, status.HTTP_200_OK)
        new_refresh = refresh_res.cookies[cookie_name].value

        # Verify token rotation: new refresh token is different
        self.assertNotEqual(initial_refresh, new_refresh)

        # Calling refresh again with OLD refresh token must fail (blacklisted)
        self.client.cookies[cookie_name] = initial_refresh
        stale_res = self.client.post(self.refresh_url, {}, format="json")
        self.assertEqual(stale_res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_blacklists_token_and_clears_cookie(self):
        User.objects.create_user(
            email="logout@malenadu.in",
            phone_number="9876543216",
            password="Password123!",
        )
        login_res = self.client.post(
            self.login_url,
            {"email": "logout@malenadu.in", "password": "Password123!"},
            format="json",
        )
        cookie_name = getattr(settings, "JWT_REFRESH_COOKIE_NAME", "refresh_token")
        refresh_token = login_res.cookies[cookie_name].value

        self.client.cookies[cookie_name] = refresh_token
        logout_res = self.client.post(self.logout_url, {}, format="json")
        self.assertEqual(logout_res.status_code, status.HTTP_200_OK)

        # Check cookie cleared (empty value or expired)
        self.assertEqual(logout_res.cookies[cookie_name].value, "")

        # Refresh token is now blacklisted
        self.client.cookies[cookie_name] = refresh_token
        refresh_attempt = self.client.post(self.refresh_url, {}, format="json")
        self.assertEqual(refresh_attempt.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_profile_me(self):
        user = User.objects.create_user(
            email="profile@malenadu.in",
            phone_number="9876543217",
            password="Password123!",
            first_name="Ganapati",
            last_name="Hegde",
        )
        # Unauthenticated request fails
        unauth_res = self.client.get(self.me_url)
        self.assertEqual(unauth_res.status_code, status.HTTP_401_UNAUTHORIZED)

        # Authenticated request succeeds
        self.client.force_authenticate(user=user)
        auth_res = self.client.get(self.me_url)
        self.assertEqual(auth_res.status_code, status.HTTP_200_OK)
        data = auth_res.json()["data"]
        self.assertEqual(data["email"], "profile@malenadu.in")
        self.assertEqual(data["first_name"], "Ganapati")

        # Update profile
        patch_res = self.client.patch(self.me_url, {"first_name": "Ganesh"}, format="json")
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_res.json()["data"]["first_name"], "Ganesh")

        # Privilege escalation attempt via patch ignored
        patch_role_res = self.client.patch(self.me_url, {"role": "SUPERADMIN"}, format="json")
        self.assertEqual(patch_role_res.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.role, Role.CUSTOMER)
