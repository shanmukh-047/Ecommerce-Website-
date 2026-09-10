from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.payments.services import WebhookService


@method_decorator(csrf_exempt, name="dispatch")
class RazorpayWebhookView(APIView):
    """
    Public ingress point for Razorpay asynchronous server-to-server notifications.
    CSRF-exempt and validated cryptographically using the webhook signature header.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        raw_body = request.body
        signature = request.headers.get("X-Razorpay-Signature", "")

        webhook_event = WebhookService.process_razorpay_webhook(
            raw_body=raw_body,
            signature=signature,
        )

        return Response(
            {
                "event_id": webhook_event.event_id,
                "status": "processed",
                "_message": "Webhook processed successfully.",
            },
            status=status.HTTP_200_OK,
        )
