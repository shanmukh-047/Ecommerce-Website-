from django.urls import path

from apps.catalog.views import StaffReviewModerationView
from .staff_views import (
    StaffCategoryListView,
    StaffProductDetailView,
    StaffProductImageUploadView,
    StaffProductListView,
)

app_name = "staff-catalog"

urlpatterns = [
    # Product CRUD
    path("products/", StaffProductListView.as_view(), name="staff-product-list"),
    path("products/<uuid:pk>/", StaffProductDetailView.as_view(), name="staff-product-detail"),
    path(
        "products/<uuid:pk>/images/",
        StaffProductImageUploadView.as_view(),
        name="staff-product-image-upload",
    ),
    path("categories/", StaffCategoryListView.as_view(), name="staff-category-list"),
    # Review moderation
    path(
        "reviews/<uuid:pk>/moderate/",
        StaffReviewModerationView.as_view(),
        name="review-moderate",
    ),
]

