from decimal import Decimal

from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order
from apps.payments.models import Payment
from apps.payments.serializers import (
    PaymentSerializer,
    PaymentSubmitUTRSerializer,
    PaymentVerifyRequestSerializer,
)
from apps.payments.services import PaymentService


class PaymentInitiateView(APIView):
    """
    Customer endpoint to initiate payment for an order in PENDING_PAYMENT status.
    Generates a gateway order and returns client checkout keys and options.
    Supports Online (Razorpay) and Cash on Delivery (COD).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        order = get_object_or_404(Order.objects.filter(user=request.user), pk=order_id)
        method = request.data.get("payment_method") or request.data.get("gateway")

        if method == "COD":
            payment = PaymentService.create_cod_payment(order=order, user=request.user)
            from apps.orders.serializers import OrderSerializer

            return Response(
                {
                    "payment": PaymentSerializer(payment).data,
                    "order": OrderSerializer(order).data,
                    "_message": "Order placed successfully with Cash on Delivery.",
                },
                status=status.HTTP_200_OK,
            )

        payment, gateway_order = PaymentService.initiate_payment(
            order=order,
            user=request.user,
        )

        key_id = getattr(settings, "RAZORPAY_KEY_ID", "rzp_test_placeholder")
        amount_in_subunits = int(Decimal(str(payment.amount)) * 100)

        return Response(
            {
                "payment": PaymentSerializer(payment).data,
                "gateway": {
                    "key_id": key_id,
                    "gateway_order_id": payment.gateway_order_id,
                    "amount": amount_in_subunits,
                    "currency": payment.currency,
                    "name": "Bharath Masala Products",
                    "description": f"Payment for Order {order.order_number}",
                },
                "_message": "Payment initiated successfully.",
            },
            status=status.HTTP_201_CREATED,
        )


class PaymentCODCreationView(APIView):
    """
    Customer endpoint to confirm order with Cash on Delivery (COD).
    Transitions order to CONFIRMED, leaves payment in PENDING status.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        order = get_object_or_404(Order.objects.filter(user=request.user), pk=order_id)
        payment = PaymentService.create_cod_payment(order=order, user=request.user)
        from apps.orders.serializers import OrderSerializer

        return Response(
            {
                "payment": PaymentSerializer(payment).data,
                "order": OrderSerializer(order).data,
                "_message": "Order placed successfully with Cash on Delivery.",
            },
            status=status.HTTP_201_CREATED,
        )


class PaymentVerifyView(APIView):
    """
    Customer endpoint to verify the HMAC-SHA256 signature returned by the gateway modal.
    Atomically transitions the order to CONFIRMED, consumes stock reservations,
    and marks payment CAPTURED.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        serializer = PaymentVerifyRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payment = PaymentService.verify_and_capture_payment(
            order_id=order_id,
            razorpay_order_id=serializer.validated_data["razorpay_order_id"],
            razorpay_payment_id=serializer.validated_data["razorpay_payment_id"],
            razorpay_signature=serializer.validated_data["razorpay_signature"],
            user=request.user,
            payment_method=serializer.validated_data.get("payment_method", ""),
        )

        return Response(
            {
                "payment": PaymentSerializer(payment).data,
                "_message": "Payment verified and captured successfully.",
            },
            status=status.HTTP_200_OK,
        )


class PaymentDetailView(APIView):
    """
    Customer endpoint retrieving payment status and attempt history for their order.
    Strictly isolated to user=request.user.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        order = get_object_or_404(Order.objects.filter(user=request.user), pk=order_id)
        payment = (
            Payment.objects.select_related("user", "order")
            .prefetch_related("attempts")
            .filter(order=order)
            .order_by("-created_at")
            .first()
        )
        if not payment:
            raise Http404("No payment record found for this order.")

        return Response(
            {
                "payment": PaymentSerializer(payment).data,
                "_message": "Payment details retrieved successfully.",
            },
            status=status.HTTP_200_OK,
        )


class PaymentSubmitUTRView(APIView):
    """
    Customer endpoint to submit a UPI transaction UTR number for manual payment verification.
    Sets payment status to PENDING_VERIFICATION.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        serializer = PaymentSubmitUTRSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        utr_number = serializer.validated_data["utr_number"]
        payment_screenshot = serializer.validated_data.get("payment_screenshot")

        payment = PaymentService.submit_utr(
            order_id=order_id,
            utr_number=utr_number,
            user=request.user,
            payment_screenshot=payment_screenshot,
        )

        return Response(
            {
                "payment": PaymentSerializer(payment).data,
                "_message": "Payment reference submitted successfully for verification.",
            },
            status=status.HTTP_200_OK,
        )

