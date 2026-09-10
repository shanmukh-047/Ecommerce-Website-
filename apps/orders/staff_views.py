from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsStaffOrManager
from apps.core.pagination import StandardResultsSetPagination
from apps.orders.models import Order
from apps.orders.serializers import OrderSerializer, OrderStatusUpdateSerializer
from apps.orders.services import OrderStateMachine


class StaffOrderListView(APIView):
    """
    Staff management endpoint to list, filter, and search all customer orders.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]

    def get(self, request):
        queryset = Order.objects.with_details().order_by("-created_at")

        # Filtering by status
        status_param = request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(order_status=status_param)

        # Filtering by payment status
        payment_status_param = request.query_params.get("payment_status")
        if payment_status_param:
            queryset = queryset.filter(payments__status=payment_status_param).distinct()

        # Filtering by payment gateway (e.g. COD, RAZORPAY)
        gateway_param = request.query_params.get("gateway")
        if gateway_param:
            queryset = queryset.filter(payments__gateway=gateway_param).distinct()

        # Filtering by wholesale flag
        wholesale_param = request.query_params.get("is_wholesale")
        if wholesale_param is not None:
            queryset = queryset.filter(is_wholesale_order=wholesale_param.lower() in ["true", "1"])

        # Search by order_number, user email, recipient phone, or recipient name
        search = request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(order_number__icontains=search)
                | Q(user__email__icontains=search)
                | Q(shipping_phone_number__icontains=search)
                | Q(shipping_recipient_name__icontains=search)
            )

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = OrderSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


class StaffOrderDetailView(APIView):
    """
    Staff detail view providing complete audit view of any order.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]

    def get(self, request, pk):
        order = get_object_or_404(
            Order.objects.with_details(),
            pk=pk,
        )
        return Response(
            {
                "order": OrderSerializer(order).data,
                "_message": "Order retrieved successfully.",
            },
            status=status.HTTP_200_OK,
        )


class StaffOrderStatusUpdateView(APIView):
    """
    Staff endpoint to transition order status through the FSM state machine.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]

    def post(self, request, pk):
        order = get_object_or_404(Order.objects.all(), pk=pk)
        serializer = OrderStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        to_status = serializer.validated_data["status"]
        notes = serializer.validated_data.get("notes", "")

        order = OrderStateMachine.transition_status(
            order=order,
            to_status=to_status,
            actor=request.user,
            notes=notes,
        )

        return Response(
            {
                "order": OrderSerializer(order).data,
                "_message": f"Order status updated to {to_status}.",
            },
            status=status.HTTP_200_OK,
        )
