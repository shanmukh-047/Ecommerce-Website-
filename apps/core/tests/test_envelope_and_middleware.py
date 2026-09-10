import io
import logging

from django.test import TestCase, override_settings
from django.urls import path, reverse
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.test import APIClient
from rest_framework.views import APIView

from apps.core.middleware import PIIMaskingFilter


class DummyValidationView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        raise ValidationError({"field": ["This field has an error."]})


class DummyPermissionView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        raise PermissionDenied("Access to this resource is forbidden.")


class DummyServerErrorView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        raise ZeroDivisionError(
            "Simulated internal catastrophic calculation failure with secret=ABCDE12345"
        )


class Dummy204View(APIView):
    permission_classes = [AllowAny]

    def delete(self, request):
        return Response(status=status.HTTP_204_NO_CONTENT)


urlpatterns = [
    path("test-validation/", DummyValidationView.as_view(), name="test-validation"),
    path("test-permission/", DummyPermissionView.as_view(), name="test-permission"),
    path("test-server-error/", DummyServerErrorView.as_view(), name="test-server-error"),
    path("test-204/", Dummy204View.as_view(), name="test-204"),
]


@override_settings(ROOT_URLCONF=__name__)
class MiddlewareAndEnvelopeTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_request_id_generated_when_absent(self):
        """X-Request-ID header must be generated and attached to response when missing."""
        response = self.client.get(reverse("test-validation"))
        self.assertIn("X-Request-ID", response.headers)
        request_id = response.headers["X-Request-ID"]
        self.assertTrue(request_id.startswith("req_"))

    def test_valid_custom_request_id_preserved(self):
        """Valid incoming X-Request-ID must be preserved."""
        custom_id = "test-req-id-12345678"
        response = self.client.get(reverse("test-validation"), HTTP_X_REQUEST_ID=custom_id)
        self.assertEqual(response.headers.get("X-Request-ID"), custom_id)
        data = response.json()
        self.assertEqual(data.get("request_id"), custom_id)

    def test_malicious_long_request_id_sanitized(self):
        """Maliciously long or invalid request IDs must be discarded and replaced."""
        malicious_id = "A" * 500  # Exceeds 64 character threshold
        response = self.client.get(reverse("test-validation"), HTTP_X_REQUEST_ID=malicious_id)
        self.assertNotEqual(response.headers.get("X-Request-ID"), malicious_id)
        self.assertTrue(response.headers.get("X-Request-ID").startswith("req_"))

    def test_validation_error_envelope(self):
        """Validation errors must return 400 Bad Request with standardized envelope."""
        response = self.client.get(reverse("test-validation"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "VALIDATION_ERROR")
        self.assertIn("field", data["error"]["details"])

    def test_permission_error_envelope(self):
        """Permission denied errors must return 403 Forbidden with standardized envelope."""
        response = self.client.get(reverse("test-permission"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "PERMISSION_DENIED")

    def test_unexpected_server_error_sanitization(self):
        """Internal server errors must return 500 with zero stack trace or internal detail leakage."""
        response = self.client.get(reverse("test-server-error"))
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "INTERNAL_SERVER_ERROR")
        self.assertNotIn("ZeroDivisionError", str(data))
        self.assertNotIn("ABCDE12345", str(data))
        self.assertEqual(data["error"]["details"], {})

    def test_http_204_returns_no_body(self):
        """HTTP 204 No Content must return empty response body."""
        response = self.client.delete(reverse("test-204"))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.content, b"")


class PIIMaskingFilterTests(TestCase):
    def setUp(self):
        self.stream = io.StringIO()
        self.handler = logging.StreamHandler(self.stream)
        self.handler.setFormatter(logging.Formatter("%(message)s"))
        self.handler.addFilter(PIIMaskingFilter())
        self.logger = logging.getLogger("tests.pii-masking")
        self.logger.handlers = [self.handler]
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

    def tearDown(self):
        self.logger.handlers.clear()

    def _output(self):
        return self.stream.getvalue()

    def test_redacts_positional_arguments_and_phone_numbers(self):
        self.logger.info("secret=%s phone=%s", "ABCDE12345", "+91 9876543210")

        output = self._output()
        self.assertNotIn("ABCDE12345", output)
        self.assertNotIn("9876543210", output)
        self.assertIn("secret=********", output)
        self.assertIn("********3210", output)

    def test_redacts_mapping_arguments(self):
        self.logger.info(
            "password=%(password)s token=%(token)s",
            {"password": "not-for-logs", "token": "jwt-value"},
        )

        output = self._output()
        self.assertNotIn("not-for-logs", output)
        self.assertNotIn("jwt-value", output)
        self.assertEqual(output.strip(), "password=******** token=********")

    def test_redacts_bearer_and_authorization_header_values(self):
        self.logger.info("Authorization: Bearer %s; token=%s", "header-token", "body-token")

        output = self._output()
        self.assertNotIn("header-token", output)
        self.assertNotIn("body-token", output)
        self.assertIn("Authorization: ********", output)

    def test_redacts_exception_message_and_traceback(self):
        try:
            raise RuntimeError("password=exception-password phone=9876543210")
        except RuntimeError:
            self.logger.exception("Request failed with secret=%s", "exception-secret")

        output = self._output()
        for sensitive_value in ["exception-secret", "exception-password", "9876543210"]:
            self.assertNotIn(sensitive_value, output)
        self.assertIn("RuntimeError: password=********", output)
