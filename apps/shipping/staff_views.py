from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsStaffOrManager
from apps.core.pagination import StandardResultsSetPagination
from apps.orders.models import Order
from apps.shipping.models import Shipment
from apps.shipping.serializers import (
    CancelShipmentRequestSerializer,
    CreateShipmentRequestSerializer,
    ShipmentSerializer,
    UpdateShipmentStatusRequestSerializer,
)
from apps.shipping.services import ShippingService


class StaffShipmentListView(APIView):
    """
    Staff management endpoint to list, filter, search, and paginate shipments.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]

    def get(self, request):
        queryset = (
            Shipment.objects.select_related("order")
            .prefetch_related("items", "items__order_line_item", "tracking_events")
            .order_by("-created_at")
        )

        status_param = request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)

        courier_param = request.query_params.get("courier")
        if courier_param:
            queryset = queryset.filter(courier_name=courier_param)

        order_id = request.query_params.get("order_id")
        if order_id:
            queryset = queryset.filter(order_id=order_id)

        search = request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(shipment_number__icontains=search)
                | Q(order__order_number__icontains=search)
                | Q(awb_number__icontains=search)
                | Q(shipping_recipient_name__icontains=search)
                | Q(shipping_phone_number__icontains=search)
            )

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = ShipmentSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class StaffShipmentDetailView(APIView):
    """
    Staff detail view providing full audit details, packaging metrics,
    carrier information, and tracking event history.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]

    def get(self, request, shipment_id):
        shipment = get_object_or_404(
            Shipment.objects.select_related("order").prefetch_related(
                "items",
                "items__order_line_item",
                "tracking_events",
            ),
            pk=shipment_id,
        )
        return Response(
            {
                "shipment": ShipmentSerializer(shipment).data,
                "_message": "Shipment retrieved successfully.",
            },
            status=status.HTTP_200_OK,
        )


class StaffOrderShipmentCreateView(APIView):
    """
    Staff endpoint to create a new shipment for an order.
    Supports full and partial/split fulfillment breakdowns.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]

    def post(self, request, order_id):
        order = get_object_or_404(Order.objects.all(), pk=order_id)
        serializer = CreateShipmentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        shipment = ShippingService.create_shipment(
            order=order,
            items_data=data.get("items"),
            courier_name=data.get("courier_name"),
            weight_in_grams=data.get("weight_in_grams"),
            length_cm=data.get("length_cm"),
            breadth_cm=data.get("breadth_cm"),
            height_cm=data.get("height_cm"),
            notes=data.get("notes", ""),
            actor=request.user,
        )

        return Response(
            {
                "shipment": ShipmentSerializer(shipment).data,
                "_message": f"Shipment {shipment.shipment_number} created successfully.",
            },
            status=status.HTTP_201_CREATED,
        )


class StaffOrderFulfillmentSummaryView(APIView):
    """
    Staff endpoint inspecting fulfilled versus remaining unfulfilled quantities per line item.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]

    def get(self, request, order_id):
        order = get_object_or_404(Order.objects.prefetch_related("lines"), pk=order_id)
        summary = ShippingService.get_order_fulfillment_summary(order)
        return Response(summary, status=status.HTTP_200_OK)


class StaffShipmentStatusUpdateView(APIView):
    """
    Staff endpoint to advance shipment status through FSM and record a tracking milestone.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]

    def post(self, request, shipment_id):
        shipment = get_object_or_404(Shipment.objects.select_related("order"), pk=shipment_id)
        serializer = UpdateShipmentStatusRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        to_status = serializer.validated_data["status"]
        location = serializer.validated_data.get("location", "")
        description = serializer.validated_data.get("description", "")

        shipment = ShippingService.transition_shipment_status(
            shipment=shipment,
            to_status=to_status,
            location=location,
            description=description,
            actor=request.user,
        )

        return Response(
            {
                "shipment": ShipmentSerializer(shipment).data,
                "_message": f"Shipment status updated to {to_status}.",
            },
            status=status.HTTP_200_OK,
        )


class StaffShipmentLabelGenerateView(APIView):
    """
    Staff endpoint to invoke carrier adapter, allocate AWB, and generate shipping label.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]

    def post(self, request, shipment_id):
        shipment = get_object_or_404(Shipment.objects.all(), pk=shipment_id)
        courier_name = request.data.get("courier_name")

        shipment = ShippingService.book_carrier_and_generate_label(
            shipment=shipment,
            courier_name=courier_name,
            actor=request.user,
        )

        return Response(
            {
                "shipment": ShipmentSerializer(shipment).data,
                "_message": f"Carrier booked and label generated for {shipment.shipment_number}.",
            },
            status=status.HTTP_200_OK,
        )


class StaffShipmentCancelView(APIView):
    """
    Staff endpoint to void a pre-dispatch shipment.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]

    def post(self, request, shipment_id):
        shipment = get_object_or_404(Shipment.objects.all(), pk=shipment_id)
        serializer = CancelShipmentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reason = serializer.validated_data.get("reason", "Cancelled by warehouse staff.")
        shipment = ShippingService.cancel_shipment(
            shipment=shipment,
            reason=reason,
            actor=request.user,
        )

        return Response(
            {
                "shipment": ShipmentSerializer(shipment).data,
                "_message": f"Shipment {shipment.shipment_number} cancelled successfully.",
            },
            status=status.HTTP_200_OK,
        )
