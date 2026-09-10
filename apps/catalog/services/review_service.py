import logging
from typing import List, Optional

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.catalog.models import (
    ModerationStatus,
    Product,
    ProductReview,
    ReviewImage,
)

logger = logging.getLogger(__name__)


class ReviewService:
    """
    Service handling customer review submission, verified purchase calculation,
    and administrative review moderation workflows.
    """

    @staticmethod
    def verify_user_purchase(user, product: Product) -> bool:
        """
        Determines whether the given user has a confirmed/delivered purchase
        of any variant belonging to the specified product.
        Delegates to OrderService.has_user_purchased_product across domain boundaries.
        """
        if not user or not getattr(user, "is_authenticated", False):
            return False

        try:
            from apps.orders.services.order_service import OrderService

            return OrderService.has_user_purchased_product(user, product)
        except Exception as e:
            logger.warning("Error verifying user purchase for review: %s", e)
            return False

    @classmethod
    def create_review(
        cls,
        user,
        product: Product,
        rating: int,
        title: str,
        review_body: str,
        images: Optional[List] = None,
    ) -> ProductReview:
        """
        Submits a customer review for administrative moderation.
        Enforces one review per user per product and ignores any client-supplied
        verification or moderation status.
        """
        if not user or not user.is_authenticated:
            raise ValidationError("Authentication is required to submit a product review.")

        if ProductReview.objects.filter(product=product, user=user).exists():
            raise ValidationError("You have already submitted a review for this product.")

        if rating < 1 or rating > 5:
            raise ValidationError("Review rating must be an integer between 1 and 5.")

        is_verified = cls.verify_user_purchase(user, product)

        with transaction.atomic():
            review = ProductReview.objects.create(
                product=product,
                user=user,
                rating=rating,
                title=title.strip(),
                review_body=review_body.strip(),
                verified_purchase=is_verified,
                moderation_status=ModerationStatus.PENDING,
            )

            if images:
                for idx, img_file in enumerate(images):
                    ReviewImage.objects.create(
                        review=review,
                        image=img_file,
                        sort_order=idx,
                    )

        logger.info(
            "Product review submitted for %s by user %s (verified=%s, status=PENDING)",
            product.slug,
            user.email,
            is_verified,
        )
        return review

    @staticmethod
    def moderate_review(review: ProductReview, action: str, staff_user) -> ProductReview:
        """
        Performs administrative review moderation (APPROVE or REJECT).
        """
        action_normalized = action.upper().strip()
        if action_normalized == "APPROVE":
            review.moderation_status = ModerationStatus.APPROVED
        elif action_normalized == "REJECT":
            review.moderation_status = ModerationStatus.REJECTED
        else:
            raise ValidationError(
                f"Invalid moderation action '{action}'. Must be 'APPROVE' or 'REJECT'."
            )

        review.save(update_fields=["moderation_status", "updated_at"])
        logger.info(
            "Product review %s moderated to %s by staff %s",
            review.id,
            review.moderation_status,
            staff_user.email if hasattr(staff_user, "email") else str(staff_user),
        )
        return review
