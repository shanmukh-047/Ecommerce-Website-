from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import StandardResultsSetPagination
from apps.orders.exceptions import OrderConflict
from apps.orders.models import Order, OrderStatus
from apps.orders.serializers import (
    CheckoutRequestSerializer,
    OrderCancelSerializer,
    OrderSerializer,
)
from apps.orders.services import CheckoutService, OrderStateMachine


class CheckoutView(APIView):
    """
    Executes atomic checkout from customer's current cart.
    Authoritatively reprices, snapshots address and line items,
    and reserves stock through InventoryService.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CheckoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order = CheckoutService.create_order_from_cart(
            user=request.user,
            shipping_address_id=serializer.validated_data["shipping_address_id"],
            customer_notes=serializer.validated_data.get("customer_notes", ""),
        )

        return Response(
            {
                "order": OrderSerializer(order).data,
                "_message": "Order placed successfully.",
            },
            status=status.HTTP_201_CREATED,
        )


class OrderListView(APIView):
    """
    Lists authenticated customer's historical orders, ordered newest first.
    Strictly isolated to user=request.user to eliminate IDOR.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = (
            Order.objects.with_details()
            .filter(user=request.user)
            .order_by("-created_at")
        )
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(orders, request)
        serializer = OrderSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


class OrderDetailView(APIView):
    """
    Retrieves full details of a customer's specific order.
    Strictly isolated to user=request.user.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        order = get_object_or_404(
            Order.objects.with_details().filter(user=request.user),
            pk=pk,
        )
        return Response(
            {
                "order": OrderSerializer(order).data,
                "_message": "Order retrieved successfully.",
            },
            status=status.HTTP_200_OK,
        )


class OrderCancelView(APIView):
    """
    Allows customers to cancel orders that are in PENDING_PAYMENT status.
    Releases active inventory reservations.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        order = get_object_or_404(Order.objects.filter(user=request.user), pk=pk)
        if order.order_status != OrderStatus.PENDING_PAYMENT:
            raise OrderConflict(
                "Only orders in PENDING_PAYMENT status can be cancelled by customers."
            )

        serializer = OrderCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get("reason", "Cancelled by customer.")

        order = OrderStateMachine.cancel_order(order, actor=request.user, reason=reason)
        return Response(
            {
                "order": OrderSerializer(order).data,
                "_message": "Order cancelled successfully.",
            },
            status=status.HTTP_200_OK,
        )
