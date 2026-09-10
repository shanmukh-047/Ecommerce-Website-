from django.urls import path

from .views import (
    PaymentCODCreationView,
    PaymentDetailView,
    PaymentInitiateView,
    PaymentSubmitUTRView,
    PaymentVerifyView,
)
from .webhook_views import RazorpayWebhookView

app_name = "payments"

urlpatterns = [
    path("orders/<uuid:order_id>/initiate/", PaymentInitiateView.as_view(), name="initiate"),
    path("orders/<uuid:order_id>/verify/", PaymentVerifyView.as_view(), name="verify"),
    path("orders/<uuid:order_id>/cod/", PaymentCODCreationView.as_view(), name="cod"),
    path("orders/<uuid:order_id>/submit-utr/", PaymentSubmitUTRView.as_view(), name="submit-utr"),
    path("orders/<uuid:order_id>/", PaymentDetailView.as_view(), name="detail"),
    path("webhooks/razorpay/", RazorpayWebhookView.as_view(), name="razorpay-webhook"),
]
