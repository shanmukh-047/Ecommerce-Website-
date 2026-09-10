from rest_framework.exceptions import APIException


class PaymentConflict(APIException):
    status_code = 409
    default_detail = "The payment operation conflicts with current order or payment state."
    default_code = "payment_conflict"


class PaymentVerificationError(APIException):
    status_code = 400
    default_detail = "Payment signature verification failed or payload is invalid."
    default_code = "payment_verification_failed"
