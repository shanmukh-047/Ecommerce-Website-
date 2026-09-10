from django.urls import path

from apps.cart.views import CartItemDetailView, CartItemListCreateView, CartView

app_name = "cart"
urlpatterns = [
    path("", CartView.as_view(), name="cart"),
    path("items/", CartItemListCreateView.as_view(), name="cart-item-list"),
    path("items/<uuid:pk>/", CartItemDetailView.as_view(), name="cart-item-detail"),
]
