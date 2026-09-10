import datetime
import logging
import uuid
from typing import Any, Optional

from django.db import transaction
from django.utils import timezone

from apps.notifications.models import NotificationEvent
from apps.returns.exceptions import ReturnConflict
from apps.returns.models import (
    ReturnRequest,
    ReturnRequestStatus,
    ReturnShipment,
    ReturnShipmentStatus,
)
from apps.returns.services.return_service import ReturnService
from apps.shipping.couriers.factory import get_courier_adapter
from apps.shipping.models import CourierProvider

logger = logging.getLogger(__name__)


class ReverseLogisticsService:
    """
    Reverse logistics orchestration service managing carrier booking,
    reverse AWB allocation, transit milestone tracking, and warehouse arrival.
    """

    @classmethod
    def generate_reverse_shipment_number(cls) -> str:
        date_str = timezone.now().strftime("%Y%m%d")
        suffix = uuid.uuid4().hex[:5].upper()
        return f"BMP-REV-{date_str}-{suffix}"

    @classmethod
    @transaction.atomic
    def schedule_reverse_pickup(
        cls,
        return_request_id: uuid.UUID,
        actor: Any,
        courier_name: str = CourierProvider.MANUAL,
        scheduled_date: Optional[datetime.date] = None,
        notes: str = "",
    ) -> ReturnShipment:
        """
        Registers reverse pickup with courier partner, allocates reverse AWB,
        snapshots the customer address, and transitions request to PICKUP_SCHEDULED.
        """
        return_request = (
            ReturnRequest.objects.select_for_update().filter(pk=return_request_id).first()
        )
        if not return_request:
            raise ReturnConflict("Return request not found.")

        if return_request.status != ReturnRequestStatus.APPROVED:
            raise ReturnConflict(
                f"Cannot schedule reverse pickup for return request in status '{return_request.status}'. "
                "Request must be APPROVED first."
            )

        if hasattr(return_request, "reverse_shipment"):
            raise ReturnConflict("Reverse shipment already booked for this return request.")

        order = return_request.order
        shipment_number = cls.generate_reverse_shipment_number()

        # Dummy carrier consignment object for adapter integration
        class ReverseConsignment:
            def __init__(self, s_num, c_name):
                self.shipment_number = s_num
                self.courier_name = c_name

        adapter = get_courier_adapter(courier_name)
        courier_res = adapter.create_shipment(ReverseConsignment(shipment_number, courier_name))
        awb = courier_res.get("awb_number") or f"REV-AWB-{uuid.uuid4().hex[:8].upper()}"

        pickup_date = scheduled_date or (timezone.now().date() + datetime.timedelta(days=1))

        shipment = ReturnShipment.objects.create(
            return_request=return_request,
            shipment_number=shipment_number,
            courier_name=courier_name,
            awb_number=awb,
            status=ReturnShipmentStatus.SCHEDULED,
            scheduled_pickup_date=pickup_date,
            pickup_recipient_name=order.shipping_recipient_name,
            pickup_phone_number=order.shipping_phone_number,
            pickup_address_line_1=order.shipping_address_line_1,
            pickup_address_line_2=order.shipping_address_line_2,
            pickup_landmark=order.shipping_landmark,
            pickup_city=order.shipping_city,
            pickup_state=order.shipping_state,
            pickup_pincode=order.shipping_pincode,
            tracking_notes=notes,
        )

        return_request.status = ReturnRequestStatus.PICKUP_SCHEDULED
        return_request.save(update_fields=["status", "updated_at"])

        logger.info(
            f"Scheduled reverse pickup {shipment_number} (AWB: {awb}) for return {return_request.return_number}."
        )

        # Dispatch notification to customer
        transaction.on_commit(
            lambda: ReturnService._dispatch_return_notification(
                return_request.id, NotificationEvent.RETURN_PICKUP_SCHEDULED
            )
        )

        return shipment

    @classmethod
    @transaction.atomic
    def update_shipment_status(
        cls,
        shipment_id: uuid.UUID,
        to_status: str,
        actor: Optional[Any] = None,
        notes: str = "",
    ) -> ReturnShipment:
        """
        Updates the reverse shipment status and synchronizes the parent ReturnRequest.
        """
        shipment = ReturnShipment.objects.select_for_update().filter(pk=shipment_id).first()
        if not shipment:
            raise ReturnConflict("Reverse shipment not found.")

        return_request = (
            ReturnRequest.objects.select_for_update().filter(pk=shipment.return_request_id).first()
        )

        now = timezone.now()
        shipment.status = to_status
        update_fields = ["status", "updated_at"]

        if to_status == ReturnShipmentStatus.PICKED_UP:
            shipment.actual_pickup_date = now
            update_fields.append("actual_pickup_date")
            if return_request.status == ReturnRequestStatus.PICKUP_SCHEDULED:
                return_request.status = ReturnRequestStatus.IN_TRANSIT
                return_request.save(update_fields=["status", "updated_at"])

        elif to_status == ReturnShipmentStatus.IN_TRANSIT:
            if return_request.status in [
                ReturnRequestStatus.APPROVED,
                ReturnRequestStatus.PICKUP_SCHEDULED,
            ]:
                return_request.status = ReturnRequestStatus.IN_TRANSIT
                return_request.save(update_fields=["status", "updated_at"])

        elif to_status == ReturnShipmentStatus.DELIVERED:
            shipment.received_at_warehouse = now
            update_fields.append("received_at_warehouse")
            if return_request.status in [
                ReturnRequestStatus.PICKUP_SCHEDULED,
                ReturnRequestStatus.IN_TRANSIT,
            ]:
                return_request.status = ReturnRequestStatus.RECEIVED
                return_request.save(update_fields=["status", "updated_at"])

                # Dispatch notification to customer: Return received at warehouse
                transaction.on_commit(
                    lambda: ReturnService._dispatch_return_notification(
                        return_request.id, NotificationEvent.RETURN_RECEIVED
                    )
                )

        if notes:
            shipment.tracking_notes = (
                f"{shipment.tracking_notes}\n[{now.isoformat()}] {notes}".strip()
            )
            update_fields.append("tracking_notes")

        shipment.save(update_fields=update_fields)
        logger.info(
            f"Reverse shipment {shipment.shipment_number} transitioned to {to_status} "
            f"(ReturnRequest: {return_request.status})."
        )
        return shipment
