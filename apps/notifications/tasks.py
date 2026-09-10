"""
Celery background tasks for apps.notifications domain.
"""

import logging
from typing import List, Optional

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="apps.notifications.tasks.dispatch_notification_task",
)
def dispatch_notification_task(self, log_id: str):
    """
    Background worker task to dispatch a single queued notification.
    """
    from apps.notifications.models import NotificationLog
    from apps.notifications.services.notification_service import NotificationService

    try:
        log = NotificationLog.objects.get(id=log_id)
        success = NotificationService.dispatch(log)
        return success
    except NotificationLog.DoesNotExist:
        logger.error(f"NotificationLog {log_id} not found.")
        return False
    except Exception as exc:
        logger.exception(f"Error dispatching notification {log_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="apps.notifications.tasks.send_order_notifications_task",
)
def send_order_notifications_task(
    self, order_id: str, event: str, channels: Optional[List[str]] = None
):
    """
    Background worker task to orchestrate multi-channel customer communications for an order.
    """
    from apps.notifications.services.notification_service import NotificationService
    from apps.orders.models import Order

    try:
        order = Order.objects.get(id=order_id)
        logs = NotificationService.send_order_notifications(
            order=order, event=event, channels=channels, async_dispatch=False
        )
        return [str(log.id) for log in logs]
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found for notification dispatch.")
        return []
    except Exception as exc:
        logger.exception(f"Error executing notifications task for order {order_id}: {exc}")
        raise self.retry(exc=exc)
