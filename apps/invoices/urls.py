"""
Customer-facing URLs for statutory tax invoice operations.
"""

from django.urls import path

from apps.invoices.views import (
    CustomerOrderCreditNoteDownloadView,
    CustomerOrderCreditNoteListView,
    CustomerOrderInvoiceDownloadView,
    CustomerOrderInvoiceHtmlView,
    CustomerOrderInvoiceView,
)

app_name = "invoices"

urlpatterns = [
    path(
        "<uuid:order_id>/invoice/",
        CustomerOrderInvoiceView.as_view(),
        name="order-invoice",
    ),
    path(
        "<uuid:order_id>/invoice/download/",
        CustomerOrderInvoiceDownloadView.as_view(),
        name="order-invoice-download",
    ),
    path(
        "<uuid:order_id>/invoice/html/",
        CustomerOrderInvoiceHtmlView.as_view(),
        name="order-invoice-html",
    ),
    path(
        "<uuid:order_id>/credit-notes/",
        CustomerOrderCreditNoteListView.as_view(),
        name="order-credit-notes",
    ),
    path(
        "<uuid:order_id>/credit-notes/<uuid:id>/download/",
        CustomerOrderCreditNoteDownloadView.as_view(),
        name="order-credit-note-download",
    ),
]
