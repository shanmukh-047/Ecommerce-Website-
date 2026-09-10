"""
Staff management URLs for statutory GST invoices.
"""

from django.urls import path

from apps.invoices.staff_views import (
    StaffCreditNoteDetailView,
    StaffCreditNoteListView,
    StaffCreditNoteRegeneratePdfView,
    StaffInvoiceDetailView,
    StaffInvoiceListView,
    StaffRegenerateInvoicePdfView,
)

app_name = "staff_invoices"

urlpatterns = [
    path("", StaffInvoiceListView.as_view(), name="invoice-list"),
    path("<uuid:id>/", StaffInvoiceDetailView.as_view(), name="invoice-detail"),
    path(
        "<uuid:id>/regenerate-pdf/",
        StaffRegenerateInvoicePdfView.as_view(),
        name="invoice-regenerate-pdf",
    ),
    path(
        "credit-notes/",
        StaffCreditNoteListView.as_view(),
        name="credit-note-list",
    ),
    path(
        "credit-notes/<uuid:id>/",
        StaffCreditNoteDetailView.as_view(),
        name="credit-note-detail",
    ),
    path(
        "credit-notes/<uuid:id>/regenerate-pdf/",
        StaffCreditNoteRegeneratePdfView.as_view(),
        name="credit-note-regenerate-pdf",
    ),
]
