import secrets
import uuid

from apps.accounts.models import Role
from apps.inventory.services import InventoryService
from apps.inventory.tests.factories import create_variant
from apps.orders.models import OrderStatus
from apps.orders.services import CheckoutService, OrderStateMachine
from apps.orders.tests.factories import (
    add_to_cart,
    create_order_address,
    create_order_user,
)
from apps.shipping.models import CourierProvider, ShipmentStatus
from apps.shipping.services import ShippingService


def create_shipping_test_order(
    user=None,
    variant=None,
    quantity=3,
    initial_stock=20,
    target_status=OrderStatus.CONFIRMED,
):
    if not user:
        unique_suffix = uuid.uuid4().hex[:6]
        user = create_order_user(
            email=f"shipping_cust_{unique_suffix}@example.com",
            phone=f"98765{secrets.randbelow(90000) + 10000}",
            role=Role.CUSTOMER,
        )
    address = create_order_address(user)
    if not variant:
        variant = create_variant(f"ship_var_{uuid.uuid4().hex[:6]}")

    InventoryService.add_stock(variant, initial_stock)
    add_to_cart(user, variant, quantity)

    order = CheckoutService.create_order_from_cart(
        user=user,
        shipping_address_id=address.id,
    )

    if target_status in [
        OrderStatus.CONFIRMED,
        OrderStatus.PROCESSING,
        OrderStatus.SHIPPED,
        OrderStatus.DELIVERED,
    ]:
        OrderStateMachine.transition_status(
            order, OrderStatus.CONFIRMED, notes="Prepaid payment verified"
        )

    if target_status in [OrderStatus.PROCESSING, OrderStatus.SHIPPED, OrderStatus.DELIVERED]:
        OrderStateMachine.transition_status(order, OrderStatus.PROCESSING, notes="Order processing")

    if target_status in [OrderStatus.SHIPPED, OrderStatus.DELIVERED]:
        OrderStateMachine.transition_status(
            order, OrderStatus.SHIPPED, notes="Dispatched via Blue Dart"
        )

    if target_status == OrderStatus.DELIVERED:
        OrderStateMachine.transition_status(
            order, OrderStatus.DELIVERED, notes="Delivered to recipient"
        )

    return order


def create_test_shipment(
    order=None,
    courier_name=CourierProvider.MANUAL,
    status=ShipmentStatus.PENDING,
    items_data=None,
    actor=None,
):
    if not order:
        order = create_shipping_test_order()

    shipment = ShippingService.create_shipment(
        order=order,
        items_data=items_data,
        courier_name=courier_name,
        actor=actor,
    )

    if status != ShipmentStatus.PENDING:
        shipment.status = status
        shipment.save()

    return shipment
