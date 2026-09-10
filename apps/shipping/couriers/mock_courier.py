import hashlib
from typing import Any, Dict, List

from django.utils import timezone

from apps.shipping.couriers.base import CourierAdapterInterface


class MockCourierAdapter(CourierAdapterInterface):
    """
    Deterministic, in-memory courier adapter for local development,
    automated testing, and offline staging environments.
    """

    def create_shipment(self, shipment: Any) -> Dict[str, Any]:
        # Deterministic AWB based on shipment number
        digest = hashlib.sha256(shipment.shipment_number.encode()).hexdigest()[:10].upper()
        awb_number = f"BMP-AWB-{digest}"
        return {
            "success": True,
            "awb_number": awb_number,
            "courier_reference": f"REF-{digest}",
            "carrier": shipment.courier_name or "MOCK_CARRIER",
            "message": "Consignment booked successfully with carrier.",
        }

    def generate_label(self, shipment: Any) -> Dict[str, Any]:
        label_url = f"https://cdn.bharathmasala.com/shipping/labels/{shipment.shipment_number}.pdf"
        return {
            "success": True,
            "label_url": label_url,
            "label_format": "PDF_4X6",
            "message": "Shipping label generated.",
        }

    def track_shipment(self, awb_number: str) -> List[Dict[str, Any]]:
        now = timezone.now()
        return [
            {
                "status": "IN_TRANSIT",
                "location": "Hubli Sorting Facility",
                "description": "Package received at regional logistics center.",
                "timestamp": now.isoformat(),
            },
            {
                "status": "READY_FOR_PICKUP",
                "location": "Sirsi Warehouse",
                "description": "Consignment packaged and manifest generated.",
                "timestamp": (now - timezone.timedelta(hours=2)).isoformat(),
            },
        ]

    def cancel_shipment(self, shipment: Any) -> bool:
        return True
