from rest_framework.exceptions import APIException


class CartConflict(APIException):
    status_code = 409
    default_detail = "The requested cart operation conflicts with current availability."
    default_code = "cart_conflict"
