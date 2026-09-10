from django.urls import path

from apps.catalog.views import (
    CategoryDetailView,
    CategoryListView,
    ProductDetailView,
    ProductListView,
    ProductReviewListCreateView,
)

app_name = "catalog"

urlpatterns = [
    # Categories
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("categories/<slug:slug>/", CategoryDetailView.as_view(), name="category-detail"),
    # Products
    path("products/", ProductListView.as_view(), name="product-list"),
    path("products/<slug:slug>/", ProductDetailView.as_view(), name="product-detail"),
    # Reviews
    path(
        "products/<slug:slug>/reviews/",
        ProductReviewListCreateView.as_view(),
        name="product-reviews",
    ),
]
