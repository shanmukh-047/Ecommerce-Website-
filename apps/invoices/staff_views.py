"""
Staff management views for statutory GST invoices.
"""

from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsStaffOrManager
from apps.invoices.models import CreditNote, Invoice
from apps.invoices.serializers import CreditNoteSerializer, InvoiceSerializer
from apps.invoices.services.credit_note_service import CreditNoteService
from apps.invoices.services.invoice_service import InvoiceService


class StaffInvoiceListView(generics.ListAPIView):
    """
    GET /api/v1/staff/invoices/
    Lists all generated tax invoices with filtering by invoice_number, date range,
    place of supply, and B2B status.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]
    serializer_class = InvoiceSerializer

    def get_queryset(self):
        queryset = (
            Invoice.objects.select_related("order", "order__user").prefetch_related("lines").all()
        )

        invoice_number = self.request.query_params.get("invoice_number")
        if invoice_number:
            queryset = queryset.filter(invoice_number__icontains=invoice_number.strip())

        order_number = self.request.query_params.get("order_number")
        if order_number:
            queryset = queryset.filter(order__order_number__icontains=order_number.strip())

        place_of_supply = self.request.query_params.get("place_of_supply")
        if place_of_supply:
            queryset = queryset.filter(place_of_supply=place_of_supply)

        is_b2b = self.request.query_params.get("is_b2b")
        if is_b2b is not None:
            if is_b2b.lower() in ("true", "1"):
                queryset = queryset.filter(is_b2b=True)
            elif is_b2b.lower() in ("false", "0"):
                queryset = queryset.filter(is_b2b=False)

        date_from = self.request.query_params.get("date_from")
        if date_from:
            queryset = queryset.filter(invoice_date__gte=date_from)

        date_to = self.request.query_params.get("date_to")
        if date_to:
            queryset = queryset.filter(invoice_date__lte=date_to)

        return queryset


class StaffInvoiceDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/staff/invoices/<uuid:id>/
    Retrieves full invoice details including statutory tax breakdown and line items.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]
    serializer_class = InvoiceSerializer
    queryset = Invoice.objects.select_related("order", "order__user").prefetch_related("lines")
    lookup_field = "id"


class StaffRegenerateInvoicePdfView(APIView):
    """
    POST /api/v1/staff/invoices/<uuid:id>/regenerate-pdf/
    Regenerates the statutory PDF document for the invoice.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]

    def post(self, request, id):
        invoice = get_object_or_404(Invoice, id=id)
        InvoiceService.regenerate_pdf(invoice)
        serializer = InvoiceSerializer(invoice, context={"request": request})
        return Response(
            {
                "detail": f"Successfully regenerated PDF for invoice {invoice.invoice_number}.",
                "invoice": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class StaffCreditNoteListView(generics.ListAPIView):
    """
    GET /api/v1/staff/invoices/credit-notes/
    Lists all statutory GST credit notes with filtering.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]
    serializer_class = CreditNoteSerializer

    def get_queryset(self):
        queryset = (
            CreditNote.objects.select_related("order", "order__user", "original_invoice")
            .prefetch_related("lines")
            .all()
        )

        credit_note_number = self.request.query_params.get("credit_note_number")
        if credit_note_number:
            queryset = queryset.filter(credit_note_number__icontains=credit_note_number.strip())

        invoice_number = self.request.query_params.get("invoice_number")
        if invoice_number:
            queryset = queryset.filter(
                original_invoice__invoice_number__icontains=invoice_number.strip()
            )

        order_number = self.request.query_params.get("order_number")
        if order_number:
            queryset = queryset.filter(order__order_number__icontains=order_number.strip())

        reason = self.request.query_params.get("reason")
        if reason:
            queryset = queryset.filter(reason=reason.strip())

        date_from = self.request.query_params.get("date_from")
        if date_from:
            queryset = queryset.filter(credit_note_date__gte=date_from)

        date_to = self.request.query_params.get("date_to")
        if date_to:
            queryset = queryset.filter(credit_note_date__lte=date_to)

        return queryset


class StaffCreditNoteDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/staff/invoices/credit-notes/<uuid:id>/
    Retrieves full details of a single statutory credit note.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]
    serializer_class = CreditNoteSerializer
    queryset = CreditNote.objects.select_related(
        "order", "order__user", "original_invoice"
    ).prefetch_related("lines")
    lookup_field = "id"


class StaffCreditNoteRegeneratePdfView(APIView):
    """
    POST /api/v1/staff/invoices/credit-notes/<uuid:id>/regenerate-pdf/
    Regenerates the statutory PDF document for the credit note.
    """

    permission_classes = [IsAuthenticated, IsStaffOrManager]

    def post(self, request, id):
        credit_note = get_object_or_404(CreditNote, id=id)
        CreditNoteService.regenerate_pdf(credit_note)
        serializer = CreditNoteSerializer(credit_note, context={"request": request})
        return Response(
            {
                "detail": f"Successfully regenerated PDF for credit note {credit_note.credit_note_number}.",
                "credit_note": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
