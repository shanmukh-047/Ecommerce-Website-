import json
from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.inventory.models import (
    MovementType,
    ReservationStatus,
    StockItem,
    StockMovement,
    StockReservation,
)
from apps.inventory.services import InventoryService
from apps.inventory.tests.factories import create_variant
from apps.orders.models import OrderStatus, OrderStatusHistory
from apps.orders.services import CheckoutService, OrderService, OrderStateMachine
from apps.orders.tasks import cleanup_expired_reservations_and_orders
from apps.orders.tests.factories import add_to_cart, create_order_address, create_order_user
from apps.payments.services import PaymentService, WebhookService
from apps.payments.tests.factories import generate_valid_signature, generate_valid_webhook_signature


def create_test_order(suffix="tsk", quantity=2, user=None):
    if not user:
        phone_suffix = str(abs(hash(suffix)) % 100000).zfill(5)
        user = create_order_user(
            email=f"user_{suffix}@example.com",
            phone=f"98765{phone_suffix}",
        )
    address = create_order_address(user)
    variant = create_variant(suffix)
    InventoryService.add_stock(variant, 50)
    add_to_cart(user, variant, quantity)
    order = CheckoutService.create_order_from_cart(user, address.id)
    return order, variant


class ReservationExpiryTaskTests(TestCase):
    def setUp(self):
        self.order, self.variant = create_test_order(suffix="exp")
        self.user = self.order.user
        self.reservation = StockReservation.objects.get(reference_id=self.order.id)
        self.stock_item = StockItem.objects.get(variant=self.variant)

    def _expire_reservation(self, res=None, minutes=5):
        target = res or self.reservation
        target.expires_at = timezone.now() - timedelta(minutes=minutes)
        target.save(update_fields=["expires_at"])

    # -------------------------------------------------------------------------
    # Reservation Expiry
    # -------------------------------------------------------------------------

    def test_active_expired_reservation_becomes_expired(self):
        self._expire_reservation()
        OrderService.expire_abandoned_orders()

        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, ReservationStatus.EXPIRED)
        self.assertIsNotNone(self.reservation.released_at)

    def test_quantity_reserved_decreases_correctly(self):
        self.assertEqual(self.stock_item.quantity_reserved, 2)
        self._expire_reservation()
        OrderService.expire_abandoned_orders()

        self.stock_item.refresh_from_db()
        self.assertEqual(self.stock_item.quantity_reserved, 0)

    def test_quantity_available_becomes_available_again(self):
        self.assertEqual(self.stock_item.quantity_available, 48)
        self._expire_reservation()
        OrderService.expire_abandoned_orders()

        self.stock_item.refresh_from_db()
        self.assertEqual(self.stock_item.quantity_available, 50)

    def test_stock_movement_expiry_ledger_created(self):
        self._expire_reservation()
        OrderService.expire_abandoned_orders()

        movement = StockMovement.objects.filter(
            stock_item=self.stock_item,
            movement_type=MovementType.EXPIRY,
        ).first()
        self.assertIsNotNone(movement)
        self.assertEqual(movement.quantity_delta, 0)
        self.assertEqual(movement.reserved_quantity_delta, -2)

    def test_non_expired_active_reservation_remains_untouched(self):
        # Reservation expires in 30 minutes (not expired)
        OrderService.expire_abandoned_orders()

        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, ReservationStatus.ACTIVE)
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.PENDING_PAYMENT)

    # -------------------------------------------------------------------------
    # Order Recovery
    # -------------------------------------------------------------------------

    def test_expired_pending_payment_order_becomes_failed(self):
        self._expire_reservation()
        OrderService.expire_abandoned_orders()

        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.FAILED)

    def test_order_status_history_created(self):
        self._expire_reservation()
        OrderService.expire_abandoned_orders()

        history = OrderStatusHistory.objects.filter(
            order=self.order,
            to_status=OrderStatus.FAILED,
        ).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.from_status, OrderStatus.PENDING_PAYMENT)

    def test_expiry_note_is_recorded(self):
        self._expire_reservation()
        OrderService.expire_abandoned_orders()

        history = OrderStatusHistory.objects.get(
            order=self.order,
            to_status=OrderStatus.FAILED,
        )
        self.assertIn("expired", history.notes.lower())

    def test_confirmed_order_is_never_changed(self):
        OrderStateMachine.transition_status(
            self.order,
            OrderStatus.CONFIRMED,
            actor=self.user,
            notes="Paid before task",
        )
        self._expire_reservation()
        OrderService.expire_abandoned_orders()

        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.CONFIRMED)

    def test_processing_order_is_never_changed(self):
        OrderStateMachine.transition_status(self.order, OrderStatus.CONFIRMED, actor=self.user)
        OrderStateMachine.transition_status(self.order, OrderStatus.PROCESSING, actor=self.user)
        self._expire_reservation()
        OrderService.expire_abandoned_orders()

        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.PROCESSING)

    def test_cancelled_order_is_never_changed(self):
        OrderStateMachine.cancel_order(self.order, actor=self.user, reason="Customer cancel")
        self._expire_reservation()
        OrderService.expire_abandoned_orders()

        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.CANCELLED)

    # -------------------------------------------------------------------------
    # Reservation Safety
    # -------------------------------------------------------------------------

    def test_consumed_reservation_is_never_released(self):
        InventoryService.consume_reservation(self.reservation.id)
        self._expire_reservation()
        OrderService.expire_abandoned_orders()

        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, ReservationStatus.CONSUMED)

    def test_released_reservation_is_ignored(self):
        InventoryService.release_reservation(self.reservation.id, expired=False)
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, ReservationStatus.RELEASED)
        self._expire_reservation()

        result = OrderService.expire_abandoned_orders()
        self.assertEqual(len(result), 0)

    def test_already_expired_reservation_is_ignored(self):
        InventoryService.release_reservation(self.reservation.id, expired=True)
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, ReservationStatus.EXPIRED)

        result = OrderService.expire_abandoned_orders()
        self.assertEqual(len(result), 0)

    def test_multiline_order_reservations_expire_correctly(self):
        # Create an order with 2 different variants
        variant_2 = create_variant("multi2")
        InventoryService.add_stock(variant_2, 30)

        user_2 = create_order_user(email="multi@example.com", phone="9876543888")
        address_2 = create_order_address(user_2)
        add_to_cart(user_2, self.variant, 2)
        add_to_cart(user_2, variant_2, 3)

        multi_order = CheckoutService.create_order_from_cart(user_2, address_2.id)
        reservations = StockReservation.objects.filter(reference_id=multi_order.id)
        self.assertEqual(reservations.count(), 2)

        for r in reservations:
            self._expire_reservation(r)

        OrderService.expire_abandoned_orders()

        for r in reservations:
            r.refresh_from_db()
            self.assertEqual(r.status, ReservationStatus.EXPIRED)

        multi_order.refresh_from_db()
        self.assertEqual(multi_order.order_status, OrderStatus.FAILED)

    # -------------------------------------------------------------------------
    # Idempotency
    # -------------------------------------------------------------------------

    def test_cleanup_twice_does_not_double_decrement_stock(self):
        self._expire_reservation()
        OrderService.expire_abandoned_orders()
        OrderService.expire_abandoned_orders()

        self.stock_item.refresh_from_db()
        self.assertEqual(self.stock_item.quantity_reserved, 0)
        self.assertEqual(self.stock_item.quantity_available, 50)

    def test_cleanup_twice_does_not_duplicate_stock_movements(self):
        self._expire_reservation()
        OrderService.expire_abandoned_orders()
        OrderService.expire_abandoned_orders()

        count = StockMovement.objects.filter(
            stock_item=self.stock_item,
            movement_type=MovementType.EXPIRY,
        ).count()
        self.assertEqual(count, 1)

    def test_cleanup_twice_does_not_duplicate_order_history(self):
        self._expire_reservation()
        OrderService.expire_abandoned_orders()
        OrderService.expire_abandoned_orders()

        failed_history_count = OrderStatusHistory.objects.filter(
            order=self.order,
            to_status=OrderStatus.FAILED,
        ).count()
        self.assertEqual(failed_history_count, 1)

    def test_already_failed_order_remains_unchanged(self):
        self._expire_reservation()
        OrderService.expire_abandoned_orders()
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.FAILED)

        # Rerun
        result = OrderService.expire_abandoned_orders()
        self.assertEqual(len(result), 0)

    # -------------------------------------------------------------------------
    # Concurrency & Racing Workflows
    # -------------------------------------------------------------------------

    def test_multiple_workers_do_not_process_same_order_twice(self):
        self._expire_reservation()
        res_1 = OrderService.expire_abandoned_orders()
        res_2 = OrderService.expire_abandoned_orders()

        self.assertEqual(len(res_1), 1)
        self.assertEqual(len(res_2), 0)

    def test_payment_verification_racing_with_expiry_behaves_safely(self):
        # Customer verifies and captures payment just before expiry task processes
        payment, _ = PaymentService.initiate_payment(self.order, self.user)
        signature = generate_valid_signature(payment.gateway_order_id, "pay_race_001")
        PaymentService.verify_and_capture_payment(
            order_id=self.order.id,
            razorpay_order_id=payment.gateway_order_id,
            razorpay_payment_id="pay_race_001",
            razorpay_signature=signature,
            user=self.user,
        )

        # Now expiry runs
        self._expire_reservation()
        result = OrderService.expire_abandoned_orders()

        self.assertEqual(len(result), 0)
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.CONFIRMED)

    def test_webhook_capture_racing_with_expiry_behaves_safely(self):
        payment, _ = PaymentService.initiate_payment(self.order, self.user)
        payload = {
            "entity": "event",
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_race_whk_001",
                        "order_id": payment.gateway_order_id,
                        "amount": int(payment.amount * 100),
                    }
                }
            },
        }
        raw_body = json.dumps(payload).encode("utf-8")
        sig = generate_valid_webhook_signature(raw_body)
        WebhookService.process_razorpay_webhook(raw_body, sig)

        # Now expiry runs
        self._expire_reservation()
        result = OrderService.expire_abandoned_orders()

        self.assertEqual(len(result), 0)
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, OrderStatus.CONFIRMED)

    # -------------------------------------------------------------------------
    # Celery Execution
    # -------------------------------------------------------------------------

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_celery_task_execution_eager(self):
        self._expire_reservation()
        result = cleanup_expired_reservations_and_orders.delay()

        self.assertTrue(result.successful())
        data = result.result
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["expired_orders_count"], 1)
        self.assertIn(self.order.order_number, data["expired_order_numbers"])

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_celery_task_rerun_remains_idempotent(self):
        self._expire_reservation()
        res_1 = cleanup_expired_reservations_and_orders.delay()
        res_2 = cleanup_expired_reservations_and_orders.delay()

        self.assertEqual(res_1.result["expired_orders_count"], 1)
        self.assertEqual(res_2.result["expired_orders_count"], 0)
