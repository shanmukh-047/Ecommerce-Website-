"""
Tests for apps.notifications background Celery tasks.
"""

from decimal import Decimal

from django.test import TestCase

from apps.accounts.models import IndianStates, User
from apps.notifications.models import (
    NotificationChannel,
    NotificationEvent,
    NotificationLog,
    NotificationStatus,
)
from apps.notifications.tasks import (
    dispatch_notification_task,
    send_order_notifications_task,
)
from apps.orders.models import Order, OrderStatus


class NotificationTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="tasks_buyer@example.com",
            phone_number="+919876543210",
            first_name="Kavita",
            last_name="Bhat",
        )
        self.order = Order.objects.create(
            order_number="BMP-TASK-001",
            user=self.user,
            order_status=OrderStatus.CONFIRMED,
            shipping_recipient_name="Kavita Bhat",
            shipping_phone_number="+919876543210",
            shipping_address_line_1="Station Road",
            shipping_city="Thirthahalli",
            shipping_state=IndianStates.KARNATAKA,
            shipping_pincode="577432",
            items_subtotal=Decimal("100.00"),
            shipping_fee=Decimal("50.00"),
            grand_total=Decimal("150.00"),
        )

    def test_dispatch_notification_task(self):
        log = NotificationLog.objects.create(
            recipient=self.user,
            recipient_target="tasks_buyer@example.com",
            channel=NotificationChannel.EMAIL,
            event=NotificationEvent.ORDER_CONFIRMED,
            idempotency_key="task-dispatch-1:ORDER_CONFIRMED:EMAIL",
            subject="Order Received",
            content="<p>Order Received</p>",
            status=NotificationStatus.PENDING,
        )
        res = dispatch_notification_task(str(log.id))
        self.assertTrue(res)

        log.refresh_from_db()
        self.assertEqual(log.status, NotificationStatus.SENT)

    def test_send_order_notifications_task(self):
        log_ids = send_order_notifications_task(
            order_id=str(self.order.id),
            event=NotificationEvent.ORDER_CONFIRMED,
        )
        self.assertEqual(len(log_ids), 3)
        self.assertEqual(NotificationLog.objects.filter(order=self.order).count(), 3)
