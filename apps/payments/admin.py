from django.contrib import admin

from .models import Payment, PaymentAttempt, PaymentWebhookEvent


class PaymentAttemptInline(admin.TabularInline):
    model = PaymentAttempt
    extra = 0
    readonly_fields = [
        "attempt_number",
        "gateway_payment_id",
        "status",
        "error_code",
        "error_description",
        "created_at",
    ]
    can_delete = False


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        "payment_number",
        "order",
        "user",
        "amount",
        "currency",
        "status",
        "gateway",
        "payment_method",
        "created_at",
    ]
    list_filter = ["status", "gateway", "created_at"]
    search_fields = [
        "payment_number",
        "order__order_number",
        "user__email",
        "gateway_order_id",
        "gateway_payment_id",
    ]
    readonly_fields = [
        "payment_number",
        "order",
        "user",
        "amount",
        "currency",
        "gateway",
        "gateway_order_id",
        "gateway_payment_id",
        "gateway_signature",
        "initiated_at",
        "authorized_at",
        "captured_at",
        "failed_at",
        "refunded_at",
        "created_at",
        "updated_at",
    ]
    inlines = [PaymentAttemptInline]


@admin.register(PaymentWebhookEvent)
class PaymentWebhookEventAdmin(admin.ModelAdmin):
    list_display = [
        "event_id",
        "provider",
        "event_type",
        "payment",
        "signature_verified",
        "processed",
        "created_at",
    ]
    list_filter = ["provider", "event_type", "processed", "signature_verified"]
    search_fields = ["event_id", "payment__payment_number"]
    readonly_fields = [
        "id",
        "provider",
        "event_id",
        "event_type",
        "payment",
        "payload",
        "signature_verified",
        "processed",
        "processed_at",
        "error_message",
        "created_at",
        "updated_at",
    ]
