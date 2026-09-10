from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


class HealthCheckTests(TestCase):
    """Automated tests for liveness and readiness health endpoints."""

    def setUp(self):
        self.client = APIClient()

    def test_liveness_probe_returns_200(self):
        """Liveness probe must return 200 without touching the database."""
        url = reverse("liveness-check")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("data", {}).get("status"), "alive")
        self.assertIn("timestamp", data.get("data", {}))

    def test_readiness_probe_returns_200_when_db_healthy(self):
        """Readiness probe returns 200 when database connectivity succeeds."""
        url = reverse("readiness-check")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("data", {}).get("status"), "ready")
        self.assertEqual(data.get("data", {}).get("services", {}).get("database"), "healthy")

    def test_readiness_probe_returns_503_when_db_unreachable(self):
        """Readiness probe returns 503 Service Unavailable when database fails."""
        url = reverse("readiness-check")
        with patch(
            "django.db.connection.cursor", side_effect=Exception("Database connection timeout")
        ):
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
            data = response.json()
            self.assertFalse(data.get("success"))
            details = data.get("error", {}).get("details", {})
            self.assertEqual(details.get("status"), "unhealthy")
            self.assertEqual(details.get("services", {}).get("database"), "unreachable")
