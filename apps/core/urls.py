from django.urls import path

from .views import LivenessCheckView, ReadinessCheckView

app_name = "core"

urlpatterns = [
    path("health/liveness/", LivenessCheckView.as_view(), name="liveness-check"),
    path("health/readiness/", ReadinessCheckView.as_view(), name="readiness-check"),
]
