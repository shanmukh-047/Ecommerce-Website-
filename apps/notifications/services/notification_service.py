"""
Notification orchestration service for multi-channel customer communications.
"""

import logging
from typing import Any, Dict, List, Optional

from django.template.loader import render_to_string

from apps.notifications.channels.factory import get_channel_adapter
from apps.notifications.exceptions import NotificationTemplateError
from apps.notifications.models import (
    NotificationChannel,
    NotificationEvent,
    NotificationLog,
    NotificationStatus,
)
from apps.orders.models import Order

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Coordinates multi-channel customer communications (Email, WhatsApp, SMS),
    guaranteeing strict deduplication, audit persistence, and graceful degradation.
    """

    EVENT_TEMPLATES = {
        NotificationEvent.ORDER_CONFIRMED: {
            "subject": "Order Confirmed - #{order_number} | Bharath Masala",
            "html": "notifications/order_confirmed.html",
            "text": "notifications/order_confirmed.txt",
        },
        NotificationEvent.ORDER_PROCESSING: {
            "subject": "Preparing Your Order - #{order_number} | Bharath Masala",
            "html": "notifications/order_confirmed.html",
            "text": "notifications/order_confirmed.txt",
        },
        NotificationEvent.ORDER_SHIPPED: {
            "subject": "Your Order Has Shipped! - #{order_number} | Bharath Masala",
            "html": "notifications/order_shipped.html",
            "text": "notifications/order_shipped.txt",
        },
        NotificationEvent.ORDER_DELIVERED: {
            "subject": "Order Delivered - #{order_number} | Bharath Masala",
            "html": "notifications/order_delivered.html",
            "text": "notifications/order_delivered.txt",
        },
        NotificationEvent.ORDER_CANCELLED: {
            "subject": "Order Cancelled - #{order_number} | Bharath Masala",
            "html": "notifications/order_cancelled.html",
            "text": "notifications/order_cancelled.txt",
        },
        NotificationEvent.REFUND_PROCESSED: {
            "subject": "Refund Processed - #{order_number} | Bharath Masala",
            "html": "notifications/refund_processed.html",
            "text": "notifications/refund_processed.txt",
        },
        NotificationEvent.CREDIT_NOTE_ISSUED: {
            "subject": "GST Credit Note Issued - #{order_number} | Bharath Masala",
            "html": "notifications/credit_note_issued.html",
            "text": "notifications/credit_note_issued.txt",
        },
        NotificationEvent.RETURN_REQUESTED: {
            "subject": "Return Request Received - #{order_number} | Bharath Masala",
            "html": "notifications/return_requested.html",
            "text": "notifications/return_requested.txt",
        },
        NotificationEvent.RETURN_APPROVED: {
            "subject": "Return Request Approved - #{order_number} | Bharath Masala",
            "html": "notifications/return_approved.html",
            "text": "notifications/return_approved.txt",
        },
        NotificationEvent.RETURN_REJECTED: {
            "subject": "Update on Your Return Request - #{order_number} | Bharath Masala",
            "html": "notifications/return_rejected.html",
            "text": "notifications/return_rejected.txt",
        },
        NotificationEvent.RETURN_PICKUP_SCHEDULED: {
            "subject": "Reverse Pickup Scheduled - #{order_number} | Bharath Masala",
            "html": "notifications/return_pickup_scheduled.html",
            "text": "notifications/return_pickup_scheduled.txt",
        },
        NotificationEvent.RETURN_RECEIVED: {
            "subject": "Return Package Received at Warehouse - #{order_number} | Bharath Masala",
            "html": "notifications/return_received.html",
            "text": "notifications/return_received.txt",
        },
        NotificationEvent.RETURN_COMPLETED: {
            "subject": "Return Completed & Resolved - #{order_number} | Bharath Masala",
            "html": "notifications/return_completed.html",
            "text": "notifications/return_completed.txt",
        },
    }

    @classmethod
    def _build_context(
        cls, order: Order, event: str, extra_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Builds standardized template rendering context from order entity.
        """
        user = order.user
        customer_name = f"{user.first_name} {user.last_name}".strip() if user else ""
        user_phone = getattr(user, "phone_number", "") or getattr(user, "phone", "") if user else ""
        if not customer_name and user:
            customer_name = user_phone or "Valued Customer"

        shipping_parts = [
            getattr(order, "shipping_address_line_1", "")
            or getattr(order, "shipping_address_line1", ""),
            getattr(order, "shipping_address_line_2", "")
            or getattr(order, "shipping_address_line2", ""),
            order.shipping_city,
            order.shipping_state,
            getattr(order, "shipping_pincode", "") or getattr(order, "shipping_postal_code", ""),
        ]
        shipping_addr = ", ".join(p for p in shipping_parts if p)

        # Retrieve shipment info if available
        shipment = getattr(order, "shipments", None)
        latest_shipment = shipment.order_by("-created_at").first() if shipment else None

        courier_name = latest_shipment.courier_name if latest_shipment else ""
        awb_number = latest_shipment.awb_number if latest_shipment else ""
        tracking_url = latest_shipment.tracking_url if latest_shipment else ""

        ctx = {
            "order": order,
            "order_number": order.order_number,
            "customer_name": customer_name,
            "user": user,
            "items": list(order.lines.all()),
            "shipping_address": shipping_addr,
            "courier_name": courier_name,
            "awb_number": awb_number,
            "tracking_url": tracking_url,
        }
        if extra_context:
            ctx.update(extra_context)
        return ctx

    @classmethod
    def _render_payload(cls, event: str, channel: str, context: Dict[str, Any]) -> tuple[str, str]:
        """
        Renders subject line and body content for the specified channel and event.
        """
        config = cls.EVENT_TEMPLATES.get(event)
        if not config:
            subject = f"Order #{context['order_number']} Update | Bharath Masala"
            content = f"Your order #{context['order_number']} status was updated to {event}."
            return subject, content

        subject = config["subject"].format(order_number=context["order_number"])

        try:
            if channel == NotificationChannel.EMAIL:
                content = render_to_string(config["html"], context)
            else:
                content = render_to_string(config["text"], context)
            return subject, content
        except Exception as exc:
            logger.error(f"Template rendering failed for {event} ({channel}): {exc}")
            raise NotificationTemplateError(
                f"Failed to render notification template: {exc}"
            ) from exc

    @classmethod
    def send_order_notifications(
        cls,
        order: Order,
        event: str,
        channels: Optional[List[str]] = None,
        extra_context: Optional[Dict[str, Any]] = None,
        async_dispatch: bool = False,
    ) -> List[NotificationLog]:
        """
        Generates and dispatches notifications for an order across channels.
        Guarantees deduplication via unique idempotency keys per order, event, and channel.
        """
        if channels is None:
            channels = [
                NotificationChannel.EMAIL,
                NotificationChannel.WHATSAPP,
                NotificationChannel.SMS,
            ]

        context = cls._build_context(order, event, extra_context)
        user = order.user
        logs = []

        for channel in channels:
            # Determine target recipient
            if channel == NotificationChannel.EMAIL:
                target = user.email if user and user.email else ""
            else:  # WHATSAPP / SMS
                user_ph = (
                    getattr(user, "phone_number", "") or getattr(user, "phone", "") if user else ""
                )
                order_ph = getattr(order, "shipping_phone_number", "") or getattr(
                    order, "shipping_phone", ""
                )
                target = order_ph or user_ph

            idempotency_key = f"{order.id}:{event}:{channel}"

            # Check existing log
            existing_log = NotificationLog.objects.filter(idempotency_key=idempotency_key).first()
            if existing_log:
                if existing_log.status == NotificationStatus.SENT:
                    logger.info(f"Notification already sent for {idempotency_key}, skipping.")
                    logs.append(existing_log)
                    continue
                log = existing_log
            else:
                subject, content = cls._render_payload(event, channel, context)
                log = NotificationLog.objects.create(
                    recipient=user,
                    recipient_target=target or "NOT_CONFIGURED",
                    channel=channel,
                    event=event,
                    order=order,
                    status=NotificationStatus.PENDING,
                    idempotency_key=idempotency_key,
                    subject=subject,
                    content=content,
                    metadata={"order_number": order.order_number, "event": event},
                )

            # Check if target is missing
            if not target:
                log.mark_skipped("Recipient contact not available for channel.")
                logs.append(log)
                continue

            if async_dispatch:
                from apps.notifications.tasks import dispatch_notification_task

                dispatch_notification_task.delay(str(log.id))
            else:
                cls.dispatch(log)

            logs.append(log)

        return logs

    @classmethod
    def dispatch(cls, log: NotificationLog) -> bool:
        """
        Dispatches an individual notification log entry through its channel adapter.
        """
        try:
            adapter = get_channel_adapter(log.channel)
            adapter.send(
                recipient_target=log.recipient_target,
                subject=log.subject,
                content=log.content,
                metadata=log.metadata,
            )
            log.mark_sent()
            return True
        except Exception as exc:
            log.mark_failed(str(exc))
            return False

    @classmethod
    def resend(cls, log: NotificationLog) -> bool:
        """
        Re-attempts dispatching an existing failed or pending notification log.
        """
        log.status = NotificationStatus.PENDING
        log.save(update_fields=["status", "updated_at"])
        return cls.dispatch(log)
