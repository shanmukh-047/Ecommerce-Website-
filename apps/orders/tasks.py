import logging

from celery import shared_task

from apps.orders.services.order_service import OrderService

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="apps.orders.tasks.cleanup_expired_reservations_and_orders",
    max_retries=3,
    default_retry_delay=30,
)
def cleanup_expired_reservations_and_orders(self):
    """
    Periodic Celery task that identifies abandoned orders in PENDING_PAYMENT status
    whose inventory reservations have expired, safely releases stock reservations back
    to the available inventory pool, and marks orders as FAILED with audit history.

    Idempotent and safe to run concurrently across multiple workers.
    """
    logger.info("Executing cleanup_expired_reservations_and_orders periodic task.")
    try:
        expired_order_numbers = OrderService.expire_abandoned_orders()
        logger.info(
            "cleanup_expired_reservations_and_orders completed. Expired %d orders: %s",
            len(expired_order_numbers),
            expired_order_numbers,
        )
        return {
            "status": "success",
            "expired_orders_count": len(expired_order_numbers),
            "expired_order_numbers": expired_order_numbers,
        }
    except Exception as exc:
        logger.error(
            "Error executing cleanup_expired_reservations_and_orders: %s",
            exc,
            exc_info=True,
        )
        raise self.retry(exc=exc)
