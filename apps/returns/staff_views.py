from rest_framework import generics, status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import IsStaffOrManager
from apps.returns.exceptions import (
    ReturnConflict,
    ReturnPermissionDenied,
    ReturnPolicyViolation,
)
from apps.returns.models import ReturnRequest, ReturnShipment
from apps.returns.serializers import (
    ReturnRequestDetailSerializer,
    ReturnRequestListSerializer,
    ReturnShipmentSerializer,
    StaffReturnCompleteSerializer,
    StaffReturnInspectionSerializer,
    StaffReturnReviewSerializer,
    StaffReversePickupScheduleSerializer,
    StaffReverseShipmentStatusSerializer,
)
from apps.returns.services.inspection_service import ReturnInspectionService
from apps.returns.services.resolution_service import ReturnResolutionService
from apps.returns.services.reverse_logistics import ReverseLogisticsService
from apps.returns.services.review_service import ReturnReviewService


class StaffReturnListView(generics.ListAPIView):
    """
    GET /api/v1/staff/returns/
    Lists all customer return requests with filtering by status and reason.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]
    serializer_class = ReturnRequestListSerializer

    def get_queryset(self):
        qs = (
            ReturnRequest.objects.all()
            .select_related("order", "user")
            .prefetch_related("items")
            .order_by("-created_at")
        )
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)

        reason_param = self.request.query_params.get("reason")
        if reason_param:
            qs = qs.filter(reason=reason_param)

        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(return_number__icontains=search) | qs.filter(
                order__order_number__icontains=search
            )

        return qs


class StaffReturnDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/staff/returns/<id>/
    Retrieves full details of a return request for staff review and processing.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]
    serializer_class = ReturnRequestDetailSerializer

    def get_object(self):
        return_id = self.kwargs.get("id")
        return_request = (
            ReturnRequest.objects.filter(pk=return_id)
            .prefetch_related("items__order_line_item", "evidence")
            .select_related(
                "order",
                "user",
                "reverse_shipment",
                "inspection",
                "credit_note",
                "replacement_order",
            )
            .first()
        )
        if not return_request:
            raise NotFound("Return request not found.")
        return return_request


class StaffReturnReviewView(generics.GenericAPIView):
    """
    POST /api/v1/staff/returns/<id>/review/
    Allows staff to approve or reject a customer return request.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]
    serializer_class = StaffReturnReviewSerializer

    def post(self, request, *args, **kwargs):
        return_id = kwargs.get("id")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        action = data["action"]
        try:
            if action == "APPROVE":
                return_request = ReturnReviewService.approve_return(
                    return_request_id=return_id,
                    actor=request.user,
                    approved_resolution=data.get("approved_resolution"),
                    review_notes=data.get("review_notes", ""),
                )
            else:
                return_request = ReturnReviewService.reject_return(
                    return_request_id=return_id,
                    actor=request.user,
                    rejection_reason=data.get("rejection_reason", ""),
                    review_notes=data.get("review_notes", ""),
                )
        except (ReturnConflict, ReturnPolicyViolation) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            ReturnRequestDetailSerializer(return_request).data, status=status.HTTP_200_OK
        )


class StaffReverseShipmentScheduleView(generics.GenericAPIView):
    """
    POST /api/v1/staff/returns/<id>/shipment/schedule/
    Books reverse courier pickup and allocates reverse AWB for an approved return.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]
    serializer_class = StaffReversePickupScheduleSerializer

    def post(self, request, *args, **kwargs):
        return_id = kwargs.get("id")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            shipment = ReverseLogisticsService.schedule_reverse_pickup(
                return_request_id=return_id,
                actor=request.user,
                courier_name=data.get("courier_name"),
                scheduled_date=data.get("scheduled_date"),
                notes=data.get("notes", ""),
            )
        except (ReturnConflict, ReturnPolicyViolation) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(ReturnShipmentSerializer(shipment).data, status=status.HTTP_201_CREATED)


class StaffReverseShipmentStatusUpdateView(generics.GenericAPIView):
    """
    POST /api/v1/staff/returns/<id>/shipment/status/
    Updates reverse shipment transit milestones (OUT_FOR_PICKUP, PICKED_UP, IN_TRANSIT, DELIVERED).
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]
    serializer_class = StaffReverseShipmentStatusSerializer

    def post(self, request, *args, **kwargs):
        return_id = kwargs.get("id")
        shipment = ReturnShipment.objects.filter(return_request_id=return_id).first()
        if not shipment:
            raise NotFound("Reverse shipment not found for this return request.")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            updated_shipment = ReverseLogisticsService.update_shipment_status(
                shipment_id=shipment.id,
                to_status=data["status"],
                actor=request.user,
                notes=data.get("notes", ""),
            )
        except (ReturnConflict, ReturnPolicyViolation) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(ReturnShipmentSerializer(updated_shipment).data, status=status.HTTP_200_OK)


class StaffReturnInspectionView(generics.GenericAPIView):
    """
    POST /api/v1/staff/returns/<id>/inspection/
    Records warehouse quality check and FSSAI inventory disposition (RESTOCK vs DISCARD).
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]
    serializer_class = StaffReturnInspectionSerializer

    def post(self, request, *args, **kwargs):
        return_id = kwargs.get("id")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            ReturnInspectionService.record_inspection(
                return_request_id=return_id,
                actor=request.user,
                result=data.get("result"),
                disposition=data.get("disposition"),
                quantity_passed=data.get("quantity_passed", 0),
                quantity_failed=data.get("quantity_failed", 0),
                notes=data.get("notes", ""),
            )
        except (ReturnConflict, ReturnPolicyViolation) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return_request = ReturnRequest.objects.get(pk=return_id)
        return Response(
            ReturnRequestDetailSerializer(return_request).data, status=status.HTTP_200_OK
        )


class StaffReturnCompleteView(generics.GenericAPIView):
    """
    POST /api/v1/staff/returns/<id>/complete/
    Executes final resolution: REFUND (CreditNote + Gateway refund) or REPLACEMENT order.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]
    serializer_class = StaffReturnCompleteSerializer

    def post(self, request, *args, **kwargs):
        return_id = kwargs.get("id")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            return_request = ReturnResolutionService.complete_return(
                return_request_id=return_id,
                actor=request.user,
                resolution_override=data.get("resolution"),
            )
        except (ReturnConflict, ReturnPolicyViolation, ReturnPermissionDenied) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            ReturnRequestDetailSerializer(return_request).data, status=status.HTTP_200_OK
        )
