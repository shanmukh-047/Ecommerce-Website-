"""
Customer-facing API endpoints for tax invoice retrieval, print rendering, and PDF downloads.
"""

from django.http import Http404, HttpResponse
from django.shortcuts import render
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.invoices.models import Invoice
from apps.invoices.serializers import InvoiceSerializer
from apps.invoices.services.invoice_service import InvoiceService
from apps.orders.models import Order


def _get_customer_order(order_id: str, user) -> Order:
    """
    Retrieves order strictly enforcing IDOR access boundaries.
    """
    try:
        if user.is_staff:
            return Order.objects.get(id=order_id)
        return Order.objects.get(id=order_id, user=user)
    except (Order.DoesNotExist, ValueError):
        raise Http404("Order not found.")


class CustomerOrderInvoiceView(APIView):
    """
    GET /api/v1/orders/<order_id>/invoice/
    Retrieves JSON metadata and tax breakdown for an order's statutory tax invoice.
    Auto-generates invoice if order is in eligible state and invoice not yet created.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        order = _get_customer_order(order_id, request.user)

        invoice = Invoice.objects.filter(order=order).first()
        if not invoice:
            if order.status in InvoiceService.ELIGIBLE_STATUSES:
                invoice = InvoiceService.generate_invoice(order)
            else:
                return Response(
                    {"detail": f"Invoice not available for order in status '{order.status}'."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        serializer = InvoiceSerializer(invoice, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class CustomerOrderInvoiceDownloadView(APIView):
    """
    GET /api/v1/orders/<order_id>/invoice/download/
    Downloads the compiled PDF file for the order's tax invoice.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        order = _get_customer_order(order_id, request.user)

        invoice = Invoice.objects.filter(order=order).first()
        if not invoice:
            if order.status in InvoiceService.ELIGIBLE_STATUSES:
                invoice = InvoiceService.generate_invoice(order)
            else:
                raise Http404("Invoice not available.")

        # Ensure PDF exists
        if not invoice.pdf_file:
            InvoiceService.regenerate_pdf(invoice)

        try:
            pdf_data = invoice.pdf_file.read()
        except Exception:
            pdf_data = InvoiceService.regenerate_pdf(invoice)

        filename = f"Invoice_{invoice.invoice_number.replace('/', '_')}.pdf"
        response = HttpResponse(pdf_data, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["Content-Length"] = len(pdf_data)
        return response


class CustomerOrderInvoiceHtmlView(APIView):
    """
    GET /api/v1/orders/<order_id>/invoice/html/
    Renders printable HTML view of the statutory GST invoice.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        order = _get_customer_order(order_id, request.user)

        invoice = Invoice.objects.filter(order=order).first()
        if not invoice:
            if order.status in InvoiceService.ELIGIBLE_STATUSES:
                invoice = InvoiceService.generate_invoice(order)
        return render(request, "invoices/tax_invoice.html", {"invoice": invoice})


class CustomerOrderCreditNoteListView(APIView):
    """
    GET /api/v1/orders/<order_id>/credit-notes/
    Lists all statutory credit notes issued for the customer's order.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        order = _get_customer_order(order_id, request.user)
        from apps.invoices.models import CreditNote
        from apps.invoices.serializers import CreditNoteSerializer

        credit_notes = (
            CreditNote.objects.filter(order=order)
            .select_related("original_invoice", "order")
            .prefetch_related("lines")
        )
        serializer = CreditNoteSerializer(credit_notes, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class CustomerOrderCreditNoteDownloadView(APIView):
    """
    GET /api/v1/orders/<order_id>/credit-notes/<uuid:id>/download/
    Downloads the compiled PDF document for a statutory tax credit note.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, order_id, id):
        order = _get_customer_order(order_id, request.user)
        from apps.invoices.models import CreditNote
        from apps.invoices.services.credit_note_service import CreditNoteService

        credit_note = (
            CreditNote.objects.filter(order=order, id=id)
            .select_related("original_invoice", "order")
            .first()
        )
        if not credit_note:
            raise Http404("Credit Note not found.")

        if not credit_note.pdf_file:
            CreditNoteService.regenerate_pdf(credit_note)

        try:
            pdf_data = credit_note.pdf_file.read()
        except Exception:
            pdf_data = CreditNoteService.regenerate_pdf(credit_note)

        filename = f"CreditNote_{credit_note.credit_note_number.replace('/', '_')}.pdf"
        response = HttpResponse(pdf_data, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["Content-Length"] = len(pdf_data)
        return response
