from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db.models import Case, Count, F, Sum, When
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsStaffOrManager
from apps.catalog.models import Product
from apps.inventory.models import StockItem
from apps.orders.models import Order, OrderStatus
from apps.orders.serializers import OrderSerializer
from apps.payments.models import Payment, PaymentStatus
from apps.payments.serializers import PaymentSerializer

User = get_user_model()


class StaffDashboardView(APIView):
    """
    GET /api/v1/staff/dashboard/ (and /api/v1/admin/dashboard/)
    Aggregates real-time business operations statistics for the Ecommerce Admin Dashboard:
    - Total Orders, Orders Today, Pending Orders
    - Total Revenue (from confirmed/delivered orders)
    - Pending Verification Payments (manual UPI QR payments waiting for review)
    - Total Active Products
    - Low Stock Variant Count
    - Total Registered Retail Customers
    - Recent 5 Orders
    - Recent 5 Payments pending verification
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]

    def get(self, request):
        now = timezone.now()
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # 1. Order metrics in a single aggregated query
        order_metrics = Order.objects.aggregate(
            total_orders=Count("id"),
            orders_today=Count(Case(When(created_at__gte=start_of_today, then=1))),
            pending_orders=Count(
                Case(
                    When(
                        order_status__in=[
                            OrderStatus.PENDING_PAYMENT,
                            OrderStatus.CONFIRMED,
                            OrderStatus.PROCESSING,
                        ],
                        then=1,
                    )
                )
            ),
            order_revenue_agg=Sum(
                Case(
                    When(
                        order_status__in=[
                            OrderStatus.CONFIRMED,
                            OrderStatus.PROCESSING,
                            OrderStatus.SHIPPED,
                            OrderStatus.DELIVERED,
                        ],
                        then="grand_total",
                    )
                )
            ),
        )
        total_orders = order_metrics["total_orders"] or 0
        orders_today = order_metrics["orders_today"] or 0
        pending_orders = order_metrics["pending_orders"] or 0
        order_revenue_agg = order_metrics["order_revenue_agg"] or Decimal("0.00")

        # 2. Payment metrics in a single aggregated query
        payment_metrics = Payment.objects.aggregate(
            captured_revenue=Sum(
                Case(When(status=PaymentStatus.CAPTURED, then="amount"))
            ),
            pending_cod_payments=Count(
                Case(When(gateway="COD", status=PaymentStatus.PENDING, then=1))
            ),
            pending_payments=Count(
                Case(When(status=PaymentStatus.PENDING_VERIFICATION, then=1))
            ),
        )
        captured_revenue = payment_metrics["captured_revenue"] or Decimal("0.00")
        pending_cod_payments = payment_metrics["pending_cod_payments"] or 0
        pending_payments = payment_metrics["pending_payments"] or 0

        # Product metrics
        total_products = Product.objects.count()

        # Inventory low-stock metrics: available stock <= reorder_level
        low_stock_products = StockItem.objects.filter(
            quantity_on_hand__lte=F("quantity_reserved") + F("reorder_level")
        ).count()

        # Customer metrics
        total_customers = User.objects.filter(is_active=True, role="CUSTOMER").count()

        # Recent 5 orders (fully prefetched via with_details)
        recent_orders = Order.objects.with_details().order_by("-created_at")[:5]

        # Recent 5 transactions across all gateways (prefetched attempts)
        recent_payments = (
            Payment.objects.select_related("order", "user")
            .prefetch_related("attempts")
            .order_by("-created_at")[:5]
        )

        return Response(
            {
                "stats": {
                    "total_orders": total_orders,
                    "orders_today": orders_today,
                    "pending_orders": pending_orders,
                    "revenue": str(captured_revenue if captured_revenue > 0 else order_revenue_agg),
                    "captured_revenue": str(captured_revenue),
                    "order_revenue": str(order_revenue_agg),
                    "pending_payments": pending_payments,
                    "pending_cod_payments": pending_cod_payments,
                    "total_products": total_products,
                    "low_stock_products": low_stock_products,
                    "total_customers": total_customers,
                },
                "recent_orders": OrderSerializer(recent_orders, many=True).data,
                "recent_payments": PaymentSerializer(recent_payments, many=True).data,
                "_message": "Admin dashboard metrics calculated successfully.",
            },
            status=status.HTTP_200_OK,
        )
