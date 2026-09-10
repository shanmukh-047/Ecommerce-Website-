from abc import ABC, abstractmethod
from typing import Any, Dict, List


class CourierAdapterInterface(ABC):
    """
    Abstract contract decoupling third-party carrier integrations (Delhivery,
    Shiprocket, Blue Dart, India Post) from core fulfillment logic.
    """

    @abstractmethod
    def create_shipment(self, shipment: Any) -> Dict[str, Any]:
        """
        Registers shipment with the courier API, books pickup, and allocates AWB.
        Returns dict containing 'awb_number', 'courier_reference', etc.
        """
        pass

    @abstractmethod
    def generate_label(self, shipment: Any) -> Dict[str, Any]:
        """
        Generates or fetches printable shipping label (PDF/thermal ZPL).
        Returns dict containing 'label_url', 'label_format', etc.
        """
        pass

    @abstractmethod
    def track_shipment(self, awb_number: str) -> List[Dict[str, Any]]:
        """
        Queries courier API for authoritative tracking events.
        Returns list of event dicts with keys: 'status', 'location', 'description', 'timestamp'.
        """
        pass

    @abstractmethod
    def cancel_shipment(self, shipment: Any) -> bool:
        """
        Cancels consignment booking with courier API before pickup.
        """
        pass
