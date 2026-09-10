"""
Celery background tasks for apps.invoices domain.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="apps.invoices.tasks.generate_invoice_for_order_task",
)
def generate_invoice_for_order_task(self, order_id: str):
    """
    Background worker task to generate statutory GST invoice for a confirmed order.
    """
    from apps.invoices.services.invoice_service import InvoiceService
    from apps.orders.models import Order

    try:
        order = Order.objects.get(id=order_id)
        invoice = InvoiceService.generate_invoice(order)
        logger.info(f"Successfully created invoice {invoice.invoice_number} for order {order_id}")
        return str(invoice.id)
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found during async invoice generation.")
        return None
    except Exception as exc:
        logger.exception(f"Error generating invoice for order {order_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="apps.invoices.tasks.regenerate_invoice_pdf_task",
)
def regenerate_invoice_pdf_task(self, invoice_id: str):
    """
    Background worker task to recompile PDF file for an existing invoice.
    """
    from apps.invoices.models import Invoice
    from apps.invoices.services.invoice_service import InvoiceService

    try:
        invoice = Invoice.objects.get(id=invoice_id)
        InvoiceService.regenerate_pdf(invoice)
        logger.info(f"Successfully recompiled PDF for invoice {invoice.invoice_number}")
        return str(invoice.id)
    except Invoice.DoesNotExist:
        logger.error(f"Invoice {invoice_id} not found for PDF regeneration.")
        return None
    except Exception as exc:
        logger.exception(f"Error regenerating PDF for invoice {invoice_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="apps.invoices.tasks.generate_credit_note_for_order_task",
)
def generate_credit_note_for_order_task(
    self,
    order_id: str,
    reason: str = "ORDER_CANCELLATION",
    reason_notes: str = "",
):
    """
    Background worker task to generate statutory GST Credit Note for an invoiced order.
    """
    from apps.invoices.services.credit_note_service import CreditNoteService
    from apps.orders.models import Order

    try:
        order = Order.objects.get(id=order_id)
        items_data = None
        if "Return to origin for shipment " in reason_notes:
            from apps.shipping.models import Shipment

            shp_num = reason_notes.split("Return to origin for shipment ")[-1].strip().rstrip(".")
            shipment = Shipment.objects.filter(shipment_number=shp_num).first()
            if shipment:
                items_data = [
                    {
                        "order_line_item_id": str(item.order_line_item_id),
                        "quantity": item.quantity,
                    }
                    for item in shipment.items.all()
                ]

        credit_note = CreditNoteService.generate_credit_note(
            order=order,
            reason=reason,
            reason_notes=reason_notes,
            items_data=items_data,
        )
        if credit_note:
            logger.info(
                f"Successfully created credit note {credit_note.credit_note_number} for order {order_id}"
            )
            return str(credit_note.id)
        return None
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found during async credit note generation.")
        return None
    except Exception as exc:
        logger.exception(f"Error generating credit note for order {order_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="apps.invoices.tasks.regenerate_credit_note_pdf_task",
)
def regenerate_credit_note_pdf_task(self, credit_note_id: str):
    """
    Background worker task to recompile PDF file for an existing credit note.
    """
    from apps.invoices.models import CreditNote
    from apps.invoices.services.credit_note_service import CreditNoteService

    try:
        credit_note = CreditNote.objects.get(id=credit_note_id)
        CreditNoteService.regenerate_pdf(credit_note)
        logger.info(f"Successfully recompiled PDF for credit note {credit_note.credit_note_number}")
        return str(credit_note.id)
    except CreditNote.DoesNotExist:
        logger.error(f"CreditNote {credit_note_id} not found for PDF regeneration.")
        return None
    except Exception as exc:
        logger.exception(f"Error regenerating PDF for credit note {credit_note_id}: {exc}")
        raise self.retry(exc=exc)
