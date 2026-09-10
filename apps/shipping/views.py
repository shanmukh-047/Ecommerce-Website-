from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order
from apps.shipping.exceptions import ShipmentNotFound
from apps.shipping.models import Shipment
from apps.shipping.serializers import PublicTrackingSerializer, ShipmentSerializer


class CustomerOrderTrackingView(APIView):
    """
    Retrieves all shipments and tracking milestones for an authenticated customer's order.
    Strictly isolated to user=request.user to eliminate IDOR vulnerabilities.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        order = get_object_or_404(
            Order.objects.filter(user=request.user),
            pk=order_id,
        )

        shipments = (
            order.shipments.all()
            .prefetch_related(
                "items",
                "items__order_line_item",
                "tracking_events",
            )
            .order_by("-created_at")
        )

        return Response(
            {
                "order_id": str(order.id),
                "order_number": order.order_number,
                "order_status": order.order_status,
                "shipped_at": order.shipped_at,
                "delivered_at": order.delivered_at,
                "shipments": ShipmentSerializer(shipments, many=True).data,
                "_message": "Tracking details retrieved successfully.",
            },
            status=status.HTTP_200_OK,
        )


class CustomerShipmentDetailView(APIView):
    """
    Retrieves full details of a specific consignment belonging to the authenticated customer.
    Enforces strict ownership check (order__user=request.user).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, shipment_number):
        shipment = get_object_or_404(
            Shipment.objects.filter(order__user=request.user).prefetch_related(
                "items",
                "items__order_line_item",
                "tracking_events",
            ),
            shipment_number=shipment_number,
        )

        return Response(
            {
                "shipment": ShipmentSerializer(shipment).data,
                "_message": "Shipment details retrieved successfully.",
            },
            status=status.HTTP_200_OK,
        )


class PublicAwbTrackingView(APIView):
    """
    Public milestone tracking endpoint for carrier tracking links (SMS/Email).
    Requires zero authentication, but strictly redacts all customer PII,
    financial data, and item breakdown.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        awb = request.query_params.get("awb", "").strip()
        shipment_num = request.query_params.get("shipment", "").strip()

        if not awb and not shipment_num:
            raise ShipmentNotFound("Query parameter 'awb' or 'shipment' is required.")

        queryset = Shipment.objects.prefetch_related("tracking_events")
        if awb:
            shipment = queryset.filter(awb_number=awb).first()
        else:
            shipment = queryset.filter(shipment_number=shipment_num).first()

        if not shipment:
            raise ShipmentNotFound("No shipment found matching the provided tracking reference.")

        return Response(
            {
                "tracking": PublicTrackingSerializer(shipment).data,
                "_message": "Public tracking details retrieved.",
            },
            status=status.HTTP_200_OK,
        )
