import json

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


class OpenAPISchemaTests(TestCase):
    """Automated tests for OpenAPI schema generation, Swagger UI, and ReDoc endpoints."""

    def setUp(self):
        self.client = APIClient()

    def test_schema_endpoint_json_returns_200(self):
        """Schema endpoint should return 200 and a valid OpenAPI 3.0 specification in JSON format."""
        url = reverse("schema")
        response = self.client.get(url, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = json.loads(response.content.decode("utf-8"))
        self.assertIn("openapi", data)
        self.assertTrue(data["openapi"].startswith("3.0"))
        self.assertIn("info", data)
        self.assertEqual(data["info"].get("title"), "Bharath Masala API")
        self.assertEqual(data["info"].get("version"), "1.0.0")
        self.assertIn("paths", data)
        self.assertGreaterEqual(len(data["paths"]), 80)
        self.assertIn("components", data)
        self.assertIn("securitySchemes", data["components"])
        self.assertIn("jwtAuth", data["components"]["securitySchemes"])

    def test_swagger_ui_endpoint_returns_200(self):
        """Swagger UI HTML endpoint should return 200."""
        url = reverse("swagger-ui")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("text/html", response.get("Content-Type", ""))
        self.assertIn(b"swagger-ui", response.content.lower())

    def test_redoc_endpoint_returns_200(self):
        """ReDoc HTML endpoint should return 200."""
        url = reverse("redoc")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("text/html", response.get("Content-Type", ""))
        self.assertIn(b"redoc", response.content.lower())
