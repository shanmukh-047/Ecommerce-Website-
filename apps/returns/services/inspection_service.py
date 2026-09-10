import logging
import uuid
from typing import Any

from django.db import transaction

from apps.inventory.models import MovementType
from apps.inventory.services import InventoryService
from apps.returns.exceptions import ReturnConflict, ReturnPolicyViolation
from apps.returns.models import (
    InspectionResult,
    InventoryDisposition,
    ReturnInspection,
    ReturnRequest,
    ReturnRequestStatus,
)

logger = logging.getLogger(__name__)


class ReturnInspectionService:
    """
    Warehouse quality assurance inspection service enforcing FSSAI food safety
    segregation (saleable restock vs scrap write-off).
    """

    @classmethod
    @transaction.atomic
    def record_inspection(
        cls,
        return_request_id: uuid.UUID,
        actor: Any,
        result: str = InspectionResult.PASSED,
        disposition: str = InventoryDisposition.RESTOCK,
        quantity_passed: int = 0,
        quantity_failed: int = 0,
        notes: str = "",
    ) -> ReturnInspection:
        """
        Records the physical warehouse inspection. If disposition is RESTOCK and result
        is PASSED, restocks physical inventory via InventoryService.add_stock.
        If disposition is DISCARD, goods are safely scrapped with zero physical restock.
        """
        return_request = (
            ReturnRequest.objects.select_for_update().filter(pk=return_request_id).first()
        )
        if not return_request:
            raise ReturnConflict("Return request not found.")

        if return_request.status != ReturnRequestStatus.RECEIVED:
            raise ReturnConflict(
                f"Cannot inspect return request in status '{return_request.status}'. "
                "Request must be RECEIVED at warehouse first."
            )

        if hasattr(return_request, "inspection"):
            raise ReturnConflict("Inspection report already exists for this return request.")

        valid_results = [
            InspectionResult.PASSED,
            InspectionResult.FAILED,
            InspectionResult.SCRAP_DAMAGED,
        ]
        if result not in valid_results:
            raise ReturnPolicyViolation(f"Invalid inspection result '{result}'.")

        valid_dispositions = [
            InventoryDisposition.RESTOCK,
            InventoryDisposition.DISCARD,
            InventoryDisposition.RETURN_TO_CUSTOMER,
        ]
        if disposition not in valid_dispositions:
            raise ReturnPolicyViolation(f"Invalid inventory disposition '{disposition}'.")

        # Validate inspection quantities
        total_returned_qty = sum(item.quantity for item in return_request.items.all())
        if quantity_passed == 0 and quantity_failed == 0 and total_returned_qty > 0:
            if result == InspectionResult.PASSED:
                quantity_passed = total_returned_qty
            else:
                quantity_failed = total_returned_qty
        elif (quantity_passed + quantity_failed) != total_returned_qty:
            raise ReturnPolicyViolation(
                f"Sum of passed ({quantity_passed}) and failed ({quantity_failed}) quantities "
                f"must equal total returned items quantity ({total_returned_qty})."
            )

        # Create Inspection Record
        inspection = ReturnInspection.objects.create(
            return_request=return_request,
            inspected_by=actor,
            result=result,
            disposition=disposition,
            quantity_passed=quantity_passed,
            quantity_failed=quantity_failed,
            notes=notes,
        )

        # FSSAI Food Safety Inventory Action
        if disposition == InventoryDisposition.RESTOCK and result == InspectionResult.PASSED:
            # Safely restock ONLY passed items into saleable inventory
            if quantity_passed > 0:
                remaining_to_restock = quantity_passed
                for item in return_request.items.select_related("order_line_item__variant").all():
                    if remaining_to_restock <= 0:
                        break
                    restock_qty = min(item.quantity, remaining_to_restock)
                    variant = item.order_line_item.variant
                    InventoryService.add_stock(
                        variant=variant,
                        quantity=restock_qty,
                        actor=actor,
                        note=f"Restock from inspected return {return_request.return_number}",
                        movement_type=MovementType.INBOUND,
                        reference_type="RETURN_RMA",
                        reference_id=return_request.id,
                    )
                    remaining_to_restock -= restock_qty
                logger.info(
                    f"Restocked {quantity_passed} passed items from return {return_request.return_number} "
                    f"into saleable inventory (failed: {quantity_failed})."
                )
        elif disposition == InventoryDisposition.DISCARD:
            logger.warning(
                f"FSSAI scrap write-off: Return {return_request.return_number} classified as DISCARD. "
                "Zero physical restock into saleable inventory."
            )

        # Transition ReturnRequest to INSPECTED
        return_request.status = ReturnRequestStatus.INSPECTED
        return_request.save(update_fields=["status", "updated_at"])

        logger.info(
            f"ReturnRequest {return_request.return_number} INSPECTED by {actor.email} "
            f"({result} / {disposition})."
        )
        return inspection
