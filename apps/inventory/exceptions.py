from rest_framework.exceptions import APIException


class InventoryConflict(APIException):
    status_code = 409
    default_detail = "The requested inventory operation conflicts with current stock state."
    default_code = "inventory_conflict"
