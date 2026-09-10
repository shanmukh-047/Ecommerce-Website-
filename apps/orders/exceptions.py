from rest_framework.exceptions import APIException


class OrderConflict(APIException):
    status_code = 409
    default_detail = "The requested order operation conflicts with current availability or state."
    default_code = "order_conflict"
