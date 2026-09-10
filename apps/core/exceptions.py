import logging

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    Throttled,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("apps.core.exceptions")


def custom_exception_handler(exc, context):
    """
    Standardized DRF Exception Handler.
    Intercepts DRF exceptions, Django standard exceptions, and unhandled errors,
    formatting them into the platform JSON error envelope while preserving exact
    HTTP status codes and suppressing sensitive internal stack traces.
    """
    request = context.get("request")
    request_id = getattr(request, "request_id", "") if request else ""

    # Convert common Django core exceptions to DRF equivalents
    if isinstance(exc, Http404):
        exc = NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = PermissionDenied()
    elif isinstance(exc, DjangoValidationError):
        if hasattr(exc, "message_dict"):
            exc = ValidationError(detail=exc.message_dict)
        else:
            exc = ValidationError(detail=exc.messages)

    # Let DRF handle standard API exceptions
    response = exception_handler(exc, context)

    if response is not None:
        status_code = response.status_code
        error_code = "API_ERROR"
        message = "An error occurred while processing your request."
        details = response.data

        if isinstance(exc, ValidationError):
            status_code = status.HTTP_400_BAD_REQUEST
            error_code = "VALIDATION_ERROR"
            message = "Input validation failed. Please check the submitted fields."
        elif isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
            status_code = status.HTTP_401_UNAUTHORIZED
            error_code = "AUTHENTICATION_FAILED"
            message = "Authentication credentials were not provided or are invalid."
        elif isinstance(exc, PermissionDenied):
            status_code = status.HTTP_403_FORBIDDEN
            error_code = "PERMISSION_DENIED"
            message = "You do not have permission to perform this action."
        elif isinstance(exc, NotFound):
            status_code = status.HTTP_404_NOT_FOUND
            error_code = "RESOURCE_NOT_FOUND"
            message = "The requested resource was not found."
        elif isinstance(exc, Throttled):
            status_code = status.HTTP_429_TOO_MANY_REQUESTS
            error_code = "RATE_LIMIT_EXCEEDED"
            wait_seconds = exc.wait
            message = f"Request limit exceeded. Available in {wait_seconds} seconds."
        elif status_code == status.HTTP_409_CONFLICT:
            error_code = "CONFLICT"
            message = "A conflict occurred with the current state of the resource."

        # Simplify detail message if DRF returned {'detail': '...'} or {'non_field_errors': [...]}
        if isinstance(details, dict):
            if "non_field_errors" in details and details["non_field_errors"]:
                message = str(details["non_field_errors"][0])
            elif "detail" in details and len(details) == 1:
                message = str(details["detail"])
                details = {}
        elif isinstance(details, list) and details:
            message = str(details[0])

        response.data = {
            "success": False,
            "request_id": request_id,
            "message": message,
            "data": None,
            "error": {
                "code": error_code,
                "details": details,
            },
        }
        return response

    # Unhandled 500 server error
    logger.error(
        "Unhandled exception [request_id=%s] on %s %s: %s",
        request_id,
        getattr(request, "method", "UNKNOWN"),
        getattr(request, "path", "UNKNOWN"),
        str(exc),
        exc_info=True,
    )

    return Response(
        {
            "success": False,
            "request_id": request_id,
            "message": "An unexpected internal server error occurred. Please try again later.",
            "data": None,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "details": {},
            },
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
