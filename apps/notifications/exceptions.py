"""
Exceptions for apps.notifications domain.
"""

from rest_framework.exceptions import APIException


class NotificationError(APIException):
    status_code = 500
    default_detail = "An error occurred during notification processing."
    default_code = "notification_error"


class ChannelDeliveryError(NotificationError):
    status_code = 502
    default_detail = "Failed to deliver message across communication channel."
    default_code = "channel_delivery_error"


class NotificationTemplateError(NotificationError):
    status_code = 500
    default_detail = "Failed to render notification template."
    default_code = "notification_template_error"
