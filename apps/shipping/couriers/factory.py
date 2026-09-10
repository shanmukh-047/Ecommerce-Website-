from typing import Dict, Type

from apps.shipping.couriers.base import CourierAdapterInterface
from apps.shipping.couriers.mock_courier import MockCourierAdapter
from apps.shipping.models import CourierProvider

_COURIER_REGISTRY: Dict[str, Type[CourierAdapterInterface]] = {
    CourierProvider.DELHIVERY: MockCourierAdapter,
    CourierProvider.BLUEDART: MockCourierAdapter,
    CourierProvider.SHIPROCKET: MockCourierAdapter,
    CourierProvider.INDIAPOST: MockCourierAdapter,
    CourierProvider.MANUAL: MockCourierAdapter,
}


def get_courier_adapter(courier_name: str) -> CourierAdapterInterface:
    """
    Factory resolving carrier name to adapter instance.
    Defaults to MockCourierAdapter for robust testability.
    """
    adapter_cls = _COURIER_REGISTRY.get(courier_name, MockCourierAdapter)
    return adapter_cls()
