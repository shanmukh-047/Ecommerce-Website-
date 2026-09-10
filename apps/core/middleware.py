import logging
import re
import traceback
import uuid
from typing import Callable

from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)

REQUEST_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{8,64}$")


class RequestIDMiddleware:
    """
    Middleware that safely extracts or generates a unique correlation request_id,
    attaches it to the request object, includes it in response headers,
    and binds it to thread-local or log record contexts.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        incoming_id = request.headers.get("X-Request-ID", "").strip()

        # Validate incoming request ID strictly
        if incoming_id and REQUEST_ID_REGEX.match(incoming_id):
            request_id = incoming_id
        else:
            request_id = f"req_{uuid.uuid4().hex}"

        request.request_id = request_id

        response = self.get_response(request)

        response["X-Request-ID"] = request_id
        return response


class PIIMaskingFilter(logging.Filter):
    """
    Logging filter that sanitizes sensitive data (PAN, GSTIN, passwords, tokens, phone numbers)
    from log records before emitting them.
    """

    PAN_PATTERN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b")
    GSTIN_PATTERN = re.compile(r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b")
    PHONE_PATTERN = re.compile(r"(\+?91[\-\s]?)?[6-9]\d{9}")
    PASSWORD_PATTERN = re.compile(
        r"(password['\"]?\s*[:=]\s*['\"]?)[^\s'\",}]+(['\"]?)", re.IGNORECASE
    )
    TOKEN_PATTERN = re.compile(r"(bearer\s+)[a-zA-Z0-9_\-\.]+", re.IGNORECASE)
    SENSITIVE_VALUE_PATTERN = re.compile(
        r"((?:token|secret|api[_-]?key)['\"]?\s*[:=]\s*['\"]?)[^\s'\",}\]]+(['\"]?)",
        re.IGNORECASE,
    )
    AUTHORIZATION_PATTERN = re.compile(
        r"((?:authorization|x-api-key)['\"]?\s*[:=]\s*['\"]?)(?:bearer\s+)?[^\s'\",}\]]+(['\"]?)",
        re.IGNORECASE,
    )

    @classmethod
    def _mask_value(cls, value: str) -> str:
        """Return a redacted representation suitable for a log message."""
        value = cls.PASSWORD_PATTERN.sub(r"\1********\2", value)
        value = cls.TOKEN_PATTERN.sub(r"\1********", value)
        value = cls.AUTHORIZATION_PATTERN.sub(r"\1********\2", value)
        value = cls.SENSITIVE_VALUE_PATTERN.sub(r"\1********\2", value)
        value = cls.PAN_PATTERN.sub(lambda m: f"{m.group(0)[:4]}****{m.group(0)[-1]}", value)
        value = cls.GSTIN_PATTERN.sub(lambda m: f"{m.group(0)[:5]}******{m.group(0)[-2:]}", value)
        return cls.PHONE_PATTERN.sub(lambda m: f"********{m.group(0)[-4:]}", value)

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            # Render before redaction so positional and mapping arguments cannot
            # bypass the filter when logging interpolates them later.
            record.msg = self._mask_value(str(record.getMessage()))
            record.args = ()
        except (TypeError, ValueError):
            # Preserve the normal logging error behaviour for malformed format
            # strings rather than introducing a second failure in this filter.
            return True

        if record.exc_info:
            exception_text = "".join(traceback.format_exception(*record.exc_info))
            record.exc_text = self._mask_value(exception_text)
            record.exc_info = None
        return True
