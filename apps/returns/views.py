import uuid

from rest_framework import generics, status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.orders.models import Order
from apps.returns.exceptions import (
    ReturnConflict,
    ReturnPermissionDenied,
    ReturnPolicyViolation,
)
from apps.returns.models import ReturnRequest
from apps.returns.serializers import (
    ReturnRequestCreateSerializer,
    ReturnRequestDetailSerializer,
    ReturnRequestListSerializer,
)
from apps.returns.services.return_service import ReturnService


class CustomerReturnBaseView:
    def get_order(self, order_id: uuid.UUID) -> Order:
        order = Order.objects.filter(pk=order_id).first()
        if not order:
            raise NotFound("Order not found.")
        user = self.request.user
        is_privileged = user.is_staff or getattr(user, "is_manager", False)
        if order.user != user and not is_privileged:
            raise NotFound("Order not found.")
        return order


class CustomerOrderReturnListCreateView(CustomerReturnBaseView, generics.ListCreateAPIView):
    """
    GET, POST /api/v1/orders/<order_id>/returns/
    Allows authenticated customers to view and submit return requests for delivered orders.
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ReturnRequestCreateSerializer
        return ReturnRequestListSerializer

    def get_queryset(self):
        order_id = self.kwargs.get("order_id")
        order = self.get_order(order_id)
        return (
            ReturnRequest.objects.filter(order=order)
            .prefetch_related("items")
            .order_by("-created_at")
        )

    def create(self, request, *args, **kwargs):
        order_id = kwargs.get("order_id")
        order = self.get_order(order_id)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        try:
            return_request = ReturnService.create_return_request(
                order_id=order.id,
                user=request.user,
                items_data=data["items"],
                reason=data["reason"],
                requested_resolution=data.get("requested_resolution"),
                customer_notes=data.get("customer_notes", ""),
                evidence_urls=data.get("evidence_urls"),
            )
        except (ReturnPolicyViolation, ReturnConflict) as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ReturnPermissionDenied as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_403_FORBIDDEN,
            )

        detail_serializer = ReturnRequestDetailSerializer(return_request)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)


class CustomerOrderReturnDetailView(CustomerReturnBaseView, generics.RetrieveAPIView):
    """
    GET /api/v1/orders/<order_id>/returns/<id>/
    Retrieves full details of a specific return request, including reverse logistics and inspection.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ReturnRequestDetailSerializer

    def get_object(self):
        order_id = self.kwargs.get("order_id")
        return_id = self.kwargs.get("id")
        order = self.get_order(order_id)

        return_request = (
            ReturnRequest.objects.filter(pk=return_id, order=order)
            .prefetch_related("items__order_line_item", "evidence")
            .select_related("reverse_shipment", "inspection", "credit_note", "replacement_order")
            .first()
        )
        if not return_request:
            raise NotFound("Return request not found.")
        return return_request


class CustomerOrderReturnCancelView(CustomerReturnBaseView, generics.GenericAPIView):
    """
    POST /api/v1/orders/<order_id>/returns/<id>/cancel/
    Allows customer to cancel a return request prior to reverse courier pickup.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ReturnRequestDetailSerializer

    def post(self, request, *args, **kwargs):
        order_id = kwargs.get("order_id")
        return_id = kwargs.get("id")
        order = self.get_order(order_id)

        return_request = ReturnRequest.objects.filter(pk=return_id, order=order).first()
        if not return_request:
            raise NotFound("Return request not found.")

        reason = request.data.get("reason", "")
        try:
            cancelled = ReturnService.cancel_return_request(
                return_request_id=return_request.id,
                user=request.user,
                reason=reason,
            )
        except (ReturnConflict, ReturnPolicyViolation) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except ReturnPermissionDenied as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

        return Response(ReturnRequestDetailSerializer(cancelled).data, status=status.HTTP_200_OK)
