import logging
import uuid

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def send_return_notification_task(self, return_request_id: str, event: str):
    """
    Asynchronously renders and dispatches multi-channel return notifications.
    """
    from apps.notifications.services.notification_service import NotificationService
    from apps.returns.models import ReturnRequest

    try:
        return_request = (
            ReturnRequest.objects.select_related("order__user")
            .filter(pk=uuid.UUID(return_request_id))
            .first()
        )
        if not return_request:
            logger.warning(f"ReturnRequest {return_request_id} not found for notification.")
            return

        order = return_request.order
        NotificationService.send_order_notifications(
            order=order,
            event=event,
            extra_context={
                "return_number": return_request.return_number,
                "order_number": order.order_number,
            },
        )
        logger.info(f"Dispatched return notification '{event}' for {return_request.return_number}.")
    except Exception as exc:
        logger.error(f"Failed to dispatch return notification for {return_request_id}: {exc}")
        raise self.retry(exc=exc)
