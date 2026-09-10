from rest_framework.exceptions import APIException


class ShipmentConflict(APIException):
    status_code = 409
    default_detail = (
        "The requested shipment operation conflicts with current state or availability."
    )
    default_code = "shipment_conflict"


class ShipmentNotFound(APIException):
    status_code = 404
    default_detail = "The requested shipment was not found."
    default_code = "shipment_not_found"


class CourierIntegrationError(APIException):
    status_code = 502
    default_detail = "Courier integration service encountered an error."
    default_code = "courier_integration_error"
