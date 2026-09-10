import logging
import uuid
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.notifications.models import NotificationEvent
from apps.returns.exceptions import ReturnConflict, ReturnPolicyViolation
from apps.returns.models import (
    ResolutionType,
    ReturnRequest,
    ReturnRequestStatus,
)
from apps.returns.services.return_service import ReturnService

logger = logging.getLogger(__name__)


class ReturnReviewService:
    """
    Staff review workflow service for approving or rejecting return requests.
    """

    @classmethod
    @transaction.atomic
    def approve_return(
        cls,
        return_request_id: uuid.UUID,
        actor: Any,
        approved_resolution: str = ResolutionType.REFUND,
        review_notes: str = "",
    ) -> ReturnRequest:
        """
        Staff approves return request, designating the final resolution mode
        (REFUND or REPLACEMENT) and unlocking reverse pickup scheduling.
        """
        return_request = (
            ReturnRequest.objects.select_for_update().filter(pk=return_request_id).first()
        )
        if not return_request:
            raise ReturnConflict("Return request not found.")

        if return_request.status != ReturnRequestStatus.PENDING_REVIEW:
            raise ReturnConflict(
                f"Cannot approve return request in status '{return_request.status}'. "
                "Only PENDING_REVIEW requests can be approved."
            )

        valid_resolutions = [ResolutionType.REFUND, ResolutionType.REPLACEMENT]
        if approved_resolution not in valid_resolutions:
            raise ReturnPolicyViolation(
                f"Invalid resolution '{approved_resolution}'. Must be one of {valid_resolutions}."
            )

        return_request.status = ReturnRequestStatus.APPROVED
        return_request.approved_resolution = approved_resolution
        return_request.reviewed_by = actor
        return_request.reviewed_at = timezone.now()
        if review_notes:
            return_request.staff_review_notes = review_notes

        return_request.save(
            update_fields=[
                "status",
                "approved_resolution",
                "reviewed_by",
                "reviewed_at",
                "staff_review_notes",
                "updated_at",
            ]
        )

        logger.info(
            f"ReturnRequest {return_request.return_number} APPROVED by staff {actor.email} "
            f"(Resolution: {approved_resolution})."
        )

        # Dispatch notification to customer
        transaction.on_commit(
            lambda: ReturnService._dispatch_return_notification(
                return_request.id, NotificationEvent.RETURN_APPROVED
            )
        )

        return return_request

    @classmethod
    @transaction.atomic
    def reject_return(
        cls,
        return_request_id: uuid.UUID,
        actor: Any,
        rejection_reason: str,
        review_notes: str = "",
    ) -> ReturnRequest:
        """
        Staff rejects return request with mandatory explanation.
        """
        if not rejection_reason or not rejection_reason.strip():
            raise ReturnPolicyViolation(
                "Rejection reason is mandatory when rejecting a return request."
            )

        return_request = (
            ReturnRequest.objects.select_for_update().filter(pk=return_request_id).first()
        )
        if not return_request:
            raise ReturnConflict("Return request not found.")

        if return_request.status != ReturnRequestStatus.PENDING_REVIEW:
            raise ReturnConflict(
                f"Cannot reject return request in status '{return_request.status}'. "
                "Only PENDING_REVIEW requests can be rejected."
            )

        return_request.status = ReturnRequestStatus.REJECTED
        return_request.rejection_reason = rejection_reason.strip()
        return_request.reviewed_by = actor
        return_request.reviewed_at = timezone.now()
        if review_notes:
            return_request.staff_review_notes = review_notes

        return_request.save(
            update_fields=[
                "status",
                "rejection_reason",
                "reviewed_by",
                "reviewed_at",
                "staff_review_notes",
                "updated_at",
            ]
        )

        logger.info(
            f"ReturnRequest {return_request.return_number} REJECTED by staff {actor.email}. "
            f"Reason: {rejection_reason}"
        )

        # Dispatch notification to customer
        transaction.on_commit(
            lambda: ReturnService._dispatch_return_notification(
                return_request.id, NotificationEvent.RETURN_REJECTED
            )
        )

        return return_request
