import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.core.models import TimeStampedModel


class PaymentStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PENDING_VERIFICATION = "PENDING_VERIFICATION", "Pending Verification"
    AUTHORIZED = "AUTHORIZED", "Authorized"
    CAPTURED = "CAPTURED", "Captured"
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED", "Partially Refunded"
    REFUNDED = "REFUNDED", "Refunded"


class PaymentMethod(models.TextChoices):
    RAZORPAY = "RAZORPAY", "Razorpay Standard"
    UPI = "UPI", "UPI"
    CARD = "CARD", "Credit/Debit Card"
    NETBANKING = "NETBANKING", "Net Banking"
    WALLET = "WALLET", "Wallet"
    COD = "COD", "Cash on Delivery"


class PaymentGateway(models.TextChoices):
    RAZORPAY = "RAZORPAY", "Razorpay"
    MANUAL = "MANUAL", "Manual / Offline"
    PHONEPE_QR = "PHONEPE_QR", "PhonePe UPI QR"
    COD = "COD", "Cash on Delivery"


class Payment(TimeStampedModel):
    """
    Authoritative payment record coordinating transaction state with orders,
    gateway tokens, amounts, and settlement timestamps.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment_number = models.CharField(max_length=32, unique=True, db_index=True)
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="payments",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="payments",
    )
    status = models.CharField(
        max_length=30,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True,
    )
    gateway = models.CharField(
        max_length=30,
        choices=PaymentGateway.choices,
        default=PaymentGateway.RAZORPAY,
        db_index=True,
    )
    payment_method = models.CharField(
        max_length=30,
        choices=PaymentMethod.choices,
        blank=True,
        default="",
    )
    gateway_order_id = models.CharField(
        max_length=100,
        blank=True,
        default="",
        db_index=True,
    )
    gateway_payment_id = models.CharField(
        max_length=100,
        blank=True,
        default="",
        db_index=True,
    )
    gateway_signature = models.CharField(max_length=255, blank=True, default="")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="INR")
    gateway_response = models.JSONField(default=dict, blank=True)
    failure_reason = models.TextField(blank=True, default="")
    utr_number = models.CharField(
        max_length=64,
        blank=True,
        default="",
        db_index=True,
        help_text="Customer-submitted 12-digit UPI UTR / RRN transaction reference number",
    )
    payment_screenshot = models.ImageField(
        upload_to="payments/screenshots/",
        null=True,
        blank=True,
        help_text="Customer-uploaded UPI payment confirmation screenshot",
    )
    refund_transaction_id = models.CharField(
        max_length=100,
        blank=True,
        default="",
        db_index=True,
    )
    amount_refunded = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    initiated_at = models.DateTimeField(auto_now_add=True)
    authorized_at = models.DateTimeField(null=True, blank=True)
    captured_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    idempotency_key = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order", "-created_at"]),
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["gateway_order_id"]),
            models.Index(fields=["gateway_payment_id"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(amount__gt=0),
                name="payment_amount_positive",
            ),
        ]

    def __str__(self):
        return f"Payment {self.payment_number} ({self.status}) - {self.currency} {self.amount}"


class PaymentAttempt(TimeStampedModel):
    """
    Log of individual payment attempts per payment session, tracking failure
    codes and gateway descriptions across customer retries without corrupting history.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name="attempts",
    )
    attempt_number = models.PositiveIntegerField(default=1)
    gateway_payment_id = models.CharField(max_length=100, blank=True, default="")
    status = models.CharField(max_length=30, choices=PaymentStatus.choices)
    error_code = models.CharField(max_length=100, blank=True, default="")
    error_description = models.TextField(blank=True, default="")
    raw_response = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["attempt_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["payment", "attempt_number"],
                name="unique_payment_attempt_number",
            ),
        ]

    def __str__(self):
        return (
            f"Payment {self.payment.payment_number} Attempt #{self.attempt_number} ({self.status})"
        )


class PaymentWebhookEvent(TimeStampedModel):
    """
    Append-only audit log for incoming gateway webhook payloads supporting
    cryptographic verification, replay prevention, and idempotency deduplication.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=50, default="RAZORPAY", db_index=True)
    event_id = models.CharField(max_length=128, unique=True, db_index=True)
    event_type = models.CharField(max_length=100, db_index=True)
    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="webhook_events",
    )
    payload = models.JSONField(default=dict)
    signature_verified = models.BooleanField(default=False)
    processed = models.BooleanField(default=False, db_index=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["provider", "event_id"]),
            models.Index(fields=["event_type", "processed"]),
        ]

    def __str__(self):
        return f"Webhook [{self.provider}] {self.event_type} (ID: {self.event_id})"
