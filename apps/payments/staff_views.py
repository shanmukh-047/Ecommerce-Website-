from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsManagerOrAdmin, IsStaffOrManager
from apps.core.pagination import StandardResultsSetPagination
from apps.payments.models import Payment
from apps.payments.serializers import (
    PaymentRefundRequestSerializer,
    PaymentRejectManualSerializer,
    PaymentSerializer,
    PaymentVerifyManualSerializer,
)
from apps.payments.services.payment_service import PaymentService


class StaffPaymentListView(APIView):
    """
    Staff management endpoint to list, filter, and inspect customer transactions.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]

    def get(self, request):
        queryset = (
            Payment.objects.select_related("order", "user")
            .prefetch_related("attempts")
            .order_by("-created_at")
        )

        status_param = request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)

        gateway_param = request.query_params.get("gateway")
        if gateway_param:
            queryset = queryset.filter(gateway=gateway_param)

        payment_method_param = request.query_params.get("payment_method")
        if payment_method_param:
            queryset = queryset.filter(payment_method=payment_method_param)

        order_id = request.query_params.get("order_id")
        if order_id:
            queryset = queryset.filter(order_id=order_id)

        search = request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(payment_number__icontains=search)
                | Q(order__order_number__icontains=search)
                | Q(user__email__icontains=search)
                | Q(gateway_payment_id__icontains=search)
                | Q(gateway_order_id__icontains=search)
                | Q(utr_number__icontains=search)
            )

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = PaymentSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class StaffPaymentDetailView(APIView):
    """
    Staff detail endpoint providing full audit log of a payment session, attempts,
    and associated gateway webhooks.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]

    def get(self, request, payment_id):
        payment = get_object_or_404(
            Payment.objects.select_related("order", "user").prefetch_related(
                "attempts", "webhook_events"
            ),
            pk=payment_id,
        )

        return Response(
            {
                "payment": PaymentSerializer(payment).data,
                "_message": "Payment retrieved successfully.",
            },
            status=status.HTTP_200_OK,
        )


class StaffPaymentRefundView(APIView):
    """
    POST /api/v1/staff/payments/<uuid:payment_id>/refund/
    Initiates a gateway refund for a captured payment. Restricted to Managers and Admins.
    """

    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    def post(self, request, payment_id):
        payment = get_object_or_404(Payment, pk=payment_id)
        serializer = PaymentRefundRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        amount = serializer.validated_data.get("amount")
        reason = serializer.validated_data.get("reason", "")

        refunded_payment = PaymentService.refund_payment(
            payment=payment,
            amount=amount,
            reason=reason,
            actor=request.user,
        )

        return Response(
            {
                "payment": PaymentSerializer(refunded_payment).data,
                "_message": f"Payment {refunded_payment.payment_number} successfully refunded.",
            },
            status=status.HTTP_200_OK,
        )


class StaffPaymentVerifyView(APIView):
    """
    POST /api/v1/staff/payments/<uuid:payment_id>/verify/
    Staff action to verify manual UPI QR payment with UTR.
    Transitions Payment to CAPTURED and Order to CONFIRMED.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]

    def post(self, request, payment_id):
        serializer = PaymentVerifyManualSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        notes = serializer.validated_data.get("notes", "")

        verified_payment = PaymentService.verify_manual_payment(
            payment_id=payment_id,
            actor=request.user,
            notes=notes,
        )

        return Response(
            {
                "payment": PaymentSerializer(verified_payment).data,
                "_message": f"Payment {verified_payment.payment_number} successfully verified and captured.",
            },
            status=status.HTTP_200_OK,
        )


class StaffPaymentRejectView(APIView):
    """
    POST /api/v1/staff/payments/<uuid:payment_id>/reject/
    Staff action to reject manual UPI QR payment.
    Transitions Payment to FAILED and records reason.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]

    def post(self, request, payment_id):
        serializer = PaymentRejectManualSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data["reason"]

        rejected_payment = PaymentService.reject_manual_payment(
            payment_id=payment_id,
            actor=request.user,
            reason=reason,
        )

        return Response(
            {
                "payment": PaymentSerializer(rejected_payment).data,
                "_message": f"Payment {rejected_payment.payment_number} marked as failed.",
            },
            status=status.HTTP_200_OK,
        )


class StaffPaymentMarkCODCollectedView(APIView):
    """
    POST /api/v1/staff/payments/<uuid:payment_id>/mark-cod-collected/
    Authorized staff action to confirm that cash has been collected for a COD order.
    Transitions Payment from PENDING to CAPTURED.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]

    def post(self, request, payment_id):
        collected_payment = PaymentService.mark_cod_collected(
            payment_id=payment_id,
            staff_user=request.user,
        )

        return Response(
            {
                "payment": PaymentSerializer(collected_payment).data,
                "_message": f"Cash on Delivery payment {collected_payment.payment_number} marked as collected.",
            },
            status=status.HTTP_200_OK,
        )

