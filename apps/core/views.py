import logging

from django.db import connection
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class LivenessCheckView(APIView):
    """
    K8s / Container Liveness Probe.
    Verifies that the web process is running and able to handle HTTP requests.
    Explicitly does NOT touch external dependencies like the database.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, *args, **kwargs):
        return Response(
            {
                "status": "alive",
                "timestamp": timezone.now().isoformat(),
            },
            status=status.HTTP_200_OK,
        )


class ReadinessCheckView(APIView):
    """
    K8s / Container Readiness Probe.
    Verifies that required backing services (database) are operational
    and ready to receive production traffic.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, *args, **kwargs):
        services_status = {}
        is_ready = True

        # Database Check
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
                cursor.fetchone()
            services_status["database"] = "healthy"
        except Exception as e:
            logger.error("Readiness probe database check failed: %s", str(e))
            services_status["database"] = "unreachable"
            is_ready = False

        if is_ready:
            return Response(
                {
                    "status": "ready",
                    "services": services_status,
                    "timestamp": timezone.now().isoformat(),
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "status": "unhealthy",
                "services": services_status,
                "timestamp": timezone.now().isoformat(),
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
