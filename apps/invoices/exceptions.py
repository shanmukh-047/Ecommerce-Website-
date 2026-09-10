from rest_framework.exceptions import APIException


class InvoiceNotFound(APIException):
    status_code = 404
    default_detail = "The requested tax invoice was not found."
    default_code = "invoice_not_found"


class InvoiceConflict(APIException):
    status_code = 409
    default_detail = (
        "The requested invoice operation conflicts with current order or payment state."
    )
    default_code = "invoice_conflict"


class InvoiceGenerationError(APIException):
    status_code = 500
    default_detail = "Failed to generate statutory tax invoice."
    default_code = "invoice_generation_error"
