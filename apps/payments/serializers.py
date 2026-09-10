from rest_framework import serializers

from apps.payments.models import Payment, PaymentAttempt, PaymentMethod, PaymentWebhookEvent


class PaymentAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentAttempt
        fields = [
            "id",
            "attempt_number",
            "gateway_payment_id",
            "status",
            "error_code",
            "error_description",
            "created_at",
        ]
        read_only_fields = fields


class PaymentSerializer(serializers.ModelSerializer):
    attempts = PaymentAttemptSerializer(many=True, read_only=True)
    customer_email = serializers.EmailField(source="user.email", read_only=True)
    customer_name = serializers.CharField(source="user.get_full_name", read_only=True)
    order_number = serializers.CharField(source="order.order_number", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "payment_number",
            "order",
            "order_number",
            "customer_email",
            "customer_name",
            "status",
            "gateway",
            "payment_method",
            "gateway_order_id",
            "gateway_payment_id",
            "utr_number",
            "payment_screenshot",
            "amount",
            "currency",
            "initiated_at",
            "authorized_at",
            "captured_at",
            "failed_at",
            "refunded_at",
            "refund_transaction_id",
            "amount_refunded",
            "failure_reason",
            "attempts",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class PaymentSubmitUTRSerializer(serializers.Serializer):
    """Customer serializer to submit UPI UTR/transaction reference number."""

    utr_number = serializers.CharField(
        min_length=6,
        max_length=32,
        required=True,
        trim_whitespace=True,
    )
    payment_screenshot = serializers.ImageField(required=False, allow_null=True)


class PaymentVerifyManualSerializer(serializers.Serializer):
    """Admin/Staff serializer to verify a pending manual UPI payment."""

    notes = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default="",
    )


class PaymentRejectManualSerializer(serializers.Serializer):
    """Admin/Staff serializer to reject an unverified UPI payment."""

    reason = serializers.CharField(
        max_length=255,
        required=True,
        trim_whitespace=True,
    )


class PaymentRefundRequestSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True,
    )
    reason = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default="",
    )


class PaymentVerifyRequestSerializer(serializers.Serializer):
    razorpay_order_id = serializers.CharField(max_length=100, required=True)
    razorpay_payment_id = serializers.CharField(max_length=100, required=True)
    razorpay_signature = serializers.CharField(max_length=255, required=True)
    payment_method = serializers.ChoiceField(
        choices=PaymentMethod.choices,
        default=PaymentMethod.RAZORPAY,
        required=False,
    )


class PaymentWebhookEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentWebhookEvent
        fields = [
            "id",
            "provider",
            "event_id",
            "event_type",
            "signature_verified",
            "processed",
            "processed_at",
            "created_at",
        ]
        read_only_fields = fields
