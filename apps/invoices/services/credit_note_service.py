"""
Statutory Indian GST Credit Note generation and management service.
Conforms to Section 34 of the CGST Act, 2017, and Rule 53(1A) of the CGST Rules, 2017.
"""

import logging
import uuid
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Optional

from django.core.files.base import ContentFile
from django.db import models, transaction
from django.utils import timezone

from apps.invoices.exceptions import InvoiceGenerationError
from apps.invoices.models import (
    CreditNote,
    CreditNoteLine,
    CreditNoteReason,
    CreditNoteSequence,
    Invoice,
    InvoiceStatus,
)
from apps.invoices.services.credit_note_pdf_generator import CreditNotePDFGenerator
from apps.invoices.services.invoice_service import InvoiceService
from apps.orders.models import Order

logger = logging.getLogger(__name__)


class CreditNoteService:
    """
    Statutory GST Tax Credit Note engine coordinating atomic consecutive numbering,
    accurate CGST/SGST/IGST tax reversals, invoice lifecycle updates,
    and zero-dependency PDF rendering.
    """

    @classmethod
    def generate_credit_note(
        cls,
        order: Order,
        reason: str = CreditNoteReason.ORDER_CANCELLATION,
        reason_notes: str = "",
        items_data: Optional[List[Dict[str, Any]]] = None,
        actor: Optional[Any] = None,
    ) -> Optional[CreditNote]:
        """
        Generates or retrieves a statutory GST Credit Note for an order that has an issued Tax Invoice.
        If no Tax Invoice was ever issued for this order, returns None (no statutory tax reversal needed).
        Guarantees strict idempotency and atomic consecutive numbering (BMP/CN/YYYY-YY/XXXXX).
        """
        with transaction.atomic():
            locked_order = Order.objects.select_for_update().get(id=order.id)
            invoice = (
                Invoice.objects.select_for_update()
                .filter(order=locked_order)
                .prefetch_related("lines")
                .first()
            )

            if not invoice:
                logger.info(
                    f"Order {locked_order.order_number} has no issued tax invoice. "
                    "Skipping credit note generation."
                )
                return None

            if invoice.status == InvoiceStatus.CANCELLED:
                raise InvoiceGenerationError(
                    f"Cannot generate credit note for cancelled invoice {invoice.invoice_number}."
                )

            # Idempotency check: for full cancellation / RTO without line overrides, return existing if already generated
            if not items_data:
                existing_cn = (
                    CreditNote.objects.filter(order=locked_order, reason=reason)
                    .prefetch_related("lines")
                    .first()
                )
                if existing_cn:
                    logger.info(
                        f"Credit note {existing_cn.credit_note_number} already exists "
                        f"for order {locked_order.order_number} ({reason})."
                    )
                    return existing_cn

            if invoice.status == InvoiceStatus.CREDIT_NOTED:
                raise InvoiceGenerationError(
                    f"Invoice {invoice.invoice_number} is already fully credited."
                )

            # Cumulative credited quantity tracking per invoice line across all credit notes for this invoice
            credited_counts = {
                row["invoice_line_id"]: row["total_qty"]
                for row in CreditNoteLine.objects.filter(credit_note__original_invoice=invoice)
                .values("invoice_line_id")
                .annotate(total_qty=models.Sum("quantity"))
            }

            invoice_lines = list(invoice.lines.all())
            items_to_credit = []

            if items_data:
                # Specific items (e.g. partial RTO or specific customer returns)
                item_qty_map = {
                    str(item["order_line_item_id"]): item["quantity"] for item in items_data
                }
                for inv_line in invoice_lines:
                    oli_id_str = str(inv_line.order_line_item_id)
                    if oli_id_str in item_qty_map:
                        requested_qty = item_qty_map[oli_id_str]
                        if requested_qty <= 0:
                            continue
                        already_credited = credited_counts.get(inv_line.id, 0)
                        remaining_eligible = inv_line.quantity - already_credited
                        if requested_qty > remaining_eligible:
                            raise InvoiceGenerationError(
                                f"Requested credit quantity ({requested_qty}) exceeds remaining eligible quantity "
                                f"({remaining_eligible}) for line '{inv_line.product_name}'."
                            )
                        items_to_credit.append((inv_line, requested_qty))
            else:
                # Full invoice crediting: credit all remaining uncredited line quantities
                for inv_line in invoice_lines:
                    already_credited = credited_counts.get(inv_line.id, 0)
                    remaining_eligible = inv_line.quantity - already_credited
                    if remaining_eligible > 0:
                        items_to_credit.append((inv_line, remaining_eligible))

            if not items_to_credit:
                raise InvoiceGenerationError(
                    f"No remaining eligible items to credit for invoice {invoice.invoice_number}."
                )

            # Allocate consecutive Credit Note Number via CreditNoteSequence
            fy = InvoiceService.get_financial_year()
            credit_note_number = CreditNoteSequence.get_next_number(fy)

            # Create Base Credit Note model snapshotting statutory seller & buyer data
            credit_note = CreditNote.objects.create(
                credit_note_number=credit_note_number,
                original_invoice=invoice,
                order=locked_order,
                credit_note_date=timezone.now().date(),
                financial_year=fy,
                reason=reason,
                reason_notes=reason_notes,
                seller_name=invoice.seller_name,
                seller_gstin=invoice.seller_gstin,
                seller_fssai=invoice.seller_fssai,
                seller_address=invoice.seller_address,
                seller_state=invoice.seller_state,
                buyer_name=invoice.buyer_name,
                buyer_email=invoice.buyer_email,
                buyer_phone=invoice.buyer_phone,
                buyer_company_name=invoice.buyer_company_name,
                buyer_gstin=invoice.buyer_gstin,
                buyer_pan=invoice.buyer_pan,
                shipping_address=invoice.shipping_address,
                place_of_supply=invoice.place_of_supply,
                is_interstate=invoice.is_interstate,
                is_b2b=invoice.is_b2b,
                items_subtotal=Decimal("0.00"),
                taxable_subtotal=Decimal("0.00"),
                cgst_amount=Decimal("0.00"),
                sgst_amount=Decimal("0.00"),
                igst_amount=Decimal("0.00"),
                total_tax=Decimal("0.00"),
                grand_total=Decimal("0.00"),
            )

            # Determine lines to credit
            taxable_subtotal = Decimal("0.00")
            cgst_total = Decimal("0.00")
            sgst_total = Decimal("0.00")
            igst_total = Decimal("0.00")
            items_subtotal = Decimal("0.00")

            for inv_line, credit_qty in items_to_credit:
                line_total = (inv_line.unit_price * credit_qty).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                items_subtotal += line_total

                rate = inv_line.gst_rate
                tax_factor = Decimal("1") + (rate / Decimal("100"))
                line_taxable = (line_total / tax_factor).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                line_tax = line_total - line_taxable
                taxable_subtotal += line_taxable

                if invoice.is_interstate:
                    cgst_r = Decimal("0.00")
                    cgst_a = Decimal("0.00")
                    sgst_r = Decimal("0.00")
                    sgst_a = Decimal("0.00")
                    igst_r = rate
                    igst_a = line_tax
                    igst_total += igst_a
                else:
                    half_rate = (rate / Decimal("2")).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                    half_tax = (line_tax / Decimal("2")).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                    cgst_r = half_rate
                    cgst_a = half_tax
                    sgst_r = half_rate
                    sgst_a = line_tax - half_tax
                    cgst_total += cgst_a
                    sgst_total += sgst_a
                    igst_r = Decimal("0.00")
                    igst_a = Decimal("0.00")

                CreditNoteLine.objects.create(
                    credit_note=credit_note,
                    invoice_line=inv_line,
                    order_line_item=inv_line.order_line_item,
                    product_name=inv_line.product_name,
                    variant_name=inv_line.variant_name,
                    sku=inv_line.sku,
                    hsn_code=inv_line.hsn_code,
                    quantity=credit_qty,
                    unit_price=inv_line.unit_price,
                    taxable_amount=line_taxable,
                    gst_rate=rate,
                    cgst_rate=cgst_r,
                    cgst_amount=cgst_a,
                    sgst_rate=sgst_r,
                    sgst_amount=sgst_a,
                    igst_rate=igst_r,
                    igst_amount=igst_a,
                    total_amount=line_total,
                )

            total_tax = igst_total if invoice.is_interstate else (cgst_total + sgst_total)
            grand_total_credited = items_subtotal

            credit_note.items_subtotal = items_subtotal
            credit_note.taxable_subtotal = taxable_subtotal
            credit_note.cgst_amount = cgst_total
            credit_note.sgst_amount = sgst_total
            credit_note.igst_amount = igst_total
            credit_note.total_tax = total_tax
            credit_note.grand_total = grand_total_credited
            credit_note.save()

            # Update original invoice status: CREDIT_NOTED only if all lines fully credited, else PARTIALLY_CREDIT_NOTED
            total_inv_qty = sum(line.quantity for line in invoice_lines)
            total_credited_qty = sum(
                credited_counts.get(line.id, 0) for line in invoice_lines
            ) + sum(qty for _, qty in items_to_credit)

            if total_credited_qty >= total_inv_qty:
                invoice.status = InvoiceStatus.CREDIT_NOTED
            elif total_credited_qty > 0:
                invoice.status = InvoiceStatus.PARTIALLY_CREDIT_NOTED
            invoice.save(update_fields=["status", "updated_at"])

            # Generate PDF file
            try:
                cls.regenerate_pdf(credit_note)
            except Exception as e:
                logger.warning(
                    f"Deferred PDF rendering for credit note {credit_note.credit_note_number}: {e}"
                )

            logger.info(
                f"Generated statutory credit note {credit_note.credit_note_number} "
                f"for invoice {invoice.invoice_number} (Order {locked_order.order_number})"
            )

            # Schedule notification hook via transaction.on_commit
            transaction.on_commit(lambda: cls._dispatch_credit_note_notification(credit_note.id))

            return credit_note

    @classmethod
    def regenerate_pdf(cls, credit_note: CreditNote) -> bytes:
        """
        Regenerates and saves the PDF file for an existing Credit Note.
        """
        try:
            pdf_bytes = CreditNotePDFGenerator.generate(credit_note)
            random_token = uuid.uuid4().hex[:12]
            filename = (
                f"CreditNote_{credit_note.credit_note_number.replace('/', '_')}_{random_token}.pdf"
            )
            credit_note.pdf_file.save(filename, ContentFile(pdf_bytes), save=False)
            credit_note.pdf_generated_at = timezone.now()
            credit_note.save(update_fields=["pdf_file", "pdf_generated_at"])
            return pdf_bytes
        except Exception as exc:
            logger.exception(
                f"Failed to regenerate PDF for credit note {credit_note.credit_note_number}: {exc}"
            )
            raise InvoiceGenerationError(f"Could not generate Credit Note PDF: {exc}") from exc

    @classmethod
    def _dispatch_credit_note_notification(cls, credit_note_id: Any) -> None:
        """
        Dispatches background task to notify the customer of credit note issuance.
        """
        try:
            from apps.notifications.models import NotificationEvent
            from apps.notifications.tasks import send_order_notifications_task

            cn = CreditNote.objects.select_related("order").get(id=credit_note_id)
            send_order_notifications_task.delay(
                str(cn.order_id),
                NotificationEvent.CREDIT_NOTE_ISSUED,
            )
        except Exception as exc:
            logger.exception(
                f"Failed to dispatch credit note notification for {credit_note_id}: {exc}"
            )
