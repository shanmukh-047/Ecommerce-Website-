from typing import List, Optional

from django.utils import timezone

from apps.promotions.models import Promotion


class PromotionService:
    """Service managing automatic promotion discovery and evaluation."""

    @classmethod
    def get_active_promotions(
        cls, is_wholesale: bool = False, category_ids: Optional[List[str]] = None
    ) -> List[Promotion]:
        """Returns all currently active promotions ordered by priority."""
        now = timezone.now()
        qs = Promotion.objects.filter(
            is_active=True,
            valid_from__lte=now,
            valid_to__gte=now,
        ).order_by("priority", "-created_at")

        if is_wholesale:
            qs = qs.filter(applicable_to_wholesale=True)

        return list(qs)
