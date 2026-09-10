"""
Statutory Indian GST Invoice generation and management service.
"""

import logging
import uuid
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import IndianStates
from apps.invoices.exceptions import InvoiceConflict, InvoiceGenerationError
from apps.invoices.models import Invoice, InvoiceLineItem, InvoiceSequence
from apps.invoices.services.pdf_generator import InvoicePDFGenerator
from apps.orders.models import Order, OrderStatus
from apps.payments.models import Payment, PaymentStatus

logger = logging.getLogger(__name__)


class InvoiceService:
    """
    Statutory GST tax invoice service handling collision-free sequential numbering,
    accurate CGST/SGST/IGST tax breakdowns, and zero-dependency PDF generation.
    """

    ELIGIBLE_STATUSES = {
        OrderStatus.CONFIRMED,
        OrderStatus.PROCESSING,
        OrderStatus.SHIPPED,
        OrderStatus.DELIVERED,
    }

    @classmethod
    def get_financial_year(cls, dt=None) -> str:
        """
        Returns Indian Financial Year string (e.g. '2026-27' for Sept 2026).
        Indian FY runs from April 1 to March 31.
        """
        if dt is None:
            dt = timezone.now()
        year = dt.year
        if dt.month >= 4:
            next_short = str(year + 1)[2:]
            return f"{year}-{next_short}"
        prev_short = str(year)[2:]
        return f"{year - 1}-{prev_short}"

    @classmethod
    def generate_invoice(cls, order: Order) -> Invoice:
        """
        Generates or retrieves the statutory GST Tax Invoice for an order.
        Guarantees strict idempotency and atomic consecutive numbering.
        """
        # 1. Check if invoice already exists (Idempotent return)
        existing = Invoice.objects.filter(order=order).first()
        if existing:
            return existing

        # 2. Validate Order Lifecycle Status
        if order.status not in cls.ELIGIBLE_STATUSES:
            raise InvoiceConflict(
                f"Cannot generate tax invoice for order in status '{order.status}'. "
                f"Order must be confirmed, processing, shipped, or delivered."
            )

        with transaction.atomic():
            # Double check inside lock to prevent race conditions
            locked_order = Order.objects.select_for_update().get(id=order.id)
            existing = Invoice.objects.filter(order=locked_order).first()
            if existing:
                return existing

            # 3. Consecutive Numbering via InvoiceSequence
            fy = cls.get_financial_year()
            seq, _ = InvoiceSequence.objects.select_for_update().get_or_create(financial_year=fy)
            seq.last_number += 1
            seq.save(update_fields=["last_number"])

            invoice_number = f"BMP/{fy}/{seq.last_number:05d}"

            # 4. Snapshot Seller Data
            seller_name = getattr(settings, "INVOICE_SELLER_NAME", "Bharath Masala Products")
            seller_gstin = getattr(settings, "INVOICE_SELLER_GSTIN", "29AAAAA0000A1Z5")
            seller_fssai = getattr(settings, "INVOICE_SELLER_FSSAI", "11223344556677")
            seller_address = getattr(
                settings,
                "INVOICE_SELLER_ADDRESS",
                "Main Road, Thirthahalli, Shimoga District, Karnataka 577432",
            )
            seller_state = IndianStates.KARNATAKA

            # 5. Snapshot Buyer Data & Wholesale Context
            user = locked_order.user
            recipient_name = getattr(locked_order, "shipping_recipient_name", "") or getattr(
                locked_order, "shipping_name", ""
            )
            user_name = f"{user.first_name} {user.last_name}".strip() if user else ""
            buyer_name = recipient_name or user_name
            user_phone = (
                getattr(user, "phone_number", "") or getattr(user, "phone", "") if user else ""
            )
            if not buyer_name and user:
                buyer_name = user_phone or "Valued Customer"
            buyer_email = user.email if user else ""
            buyer_phone = (
                getattr(locked_order, "shipping_phone_number", "")
                or getattr(locked_order, "shipping_phone", "")
                or user_phone
            )

            # Check for B2B Wholesale Profile
            is_b2b = bool(locked_order.is_wholesale_order)
            buyer_company = ""
            buyer_gstin = ""
            buyer_pan = ""

            if user and hasattr(user, "wholesale_profile") and user.wholesale_profile:
                wp = user.wholesale_profile
                buyer_company = getattr(wp, "company_name", "") or ""
                buyer_gstin = getattr(wp, "gstin", "") or ""
                buyer_pan = getattr(wp, "pan_number", "") or getattr(wp, "pan", "") or ""

            shipping_address_parts = [
                getattr(locked_order, "shipping_address_line_1", "")
                or getattr(locked_order, "shipping_address_line1", ""),
                getattr(locked_order, "shipping_address_line_2", "")
                or getattr(locked_order, "shipping_address_line2", ""),
                locked_order.shipping_city,
                locked_order.shipping_state,
                getattr(locked_order, "shipping_pincode", "")
                or getattr(locked_order, "shipping_postal_code", ""),
            ]
            full_shipping_address = ", ".join(p for p in shipping_address_parts if p)

            # 6. Place of Supply & Inter-State Calculation
            place_of_supply = locked_order.shipping_state
            is_interstate = place_of_supply != seller_state

            # 7. Payment snapshot
            captured_payment = (
                Payment.objects.filter(order=locked_order, status=PaymentStatus.CAPTURED)
                .order_by("-created_at")
                .first()
            )
            payment_method = (
                getattr(captured_payment, "payment_method", "")
                or getattr(captured_payment, "method", "")
                if captured_payment
                else ""
            )
            payment_txn = captured_payment.gateway_payment_id if captured_payment else ""

            # 8. Create Base Invoice Model
            invoice = Invoice.objects.create(
                invoice_number=invoice_number,
                order=locked_order,
                invoice_date=timezone.now().date(),
                seller_name=seller_name,
                seller_gstin=seller_gstin,
                seller_fssai=seller_fssai,
                seller_address=seller_address,
                seller_state=seller_state,
                buyer_name=buyer_name,
                buyer_email=buyer_email,
                buyer_phone=buyer_phone,
                buyer_company_name=buyer_company,
                buyer_gstin=buyer_gstin,
                buyer_pan=buyer_pan,
                shipping_address=full_shipping_address,
                place_of_supply=place_of_supply,
                is_interstate=is_interstate,
                is_b2b=is_b2b,
                items_subtotal=Decimal("0.00"),
                total_discount=Decimal("0.00"),
                taxable_subtotal=Decimal("0.00"),
                cgst_amount=Decimal("0.00"),
                sgst_amount=Decimal("0.00"),
                igst_amount=Decimal("0.00"),
                total_tax=Decimal("0.00"),
                shipping_fee=locked_order.shipping_fee,
                grand_total=Decimal("0.00"),
                payment_method=payment_method,
                payment_transaction_id=payment_txn,
            )

            # 9. Line Item Tax Breakdown with Proportional Discount Allocation
            taxable_subtotal = Decimal("0.00")
            cgst_total = Decimal("0.00")
            sgst_total = Decimal("0.00")
            igst_total = Decimal("0.00")
            items_subtotal = Decimal("0.00")

            order_discount = getattr(locked_order, "total_discount", Decimal("0.00")) or Decimal(
                "0.00"
            )
            order_lines = list(
                locked_order.lines.select_related("variant", "variant__product").all()
            )
            order_items_gross = sum(line.line_subtotal for line in order_lines)

            # Cap discount at items gross to prevent negative net totals
            effective_discount = min(order_discount, order_items_gross)

            # Proportional allocation of order-level discount across line items using
            # Largest Remainder Method (Hamilton-Hare Method) to strictly guarantee:
            # 1. sum(line_disc) == effective_discount
            # 2. 0 <= line_disc <= line.line_subtotal
            # 3. No negative remainder or rounding drift occurs across any line combinations.
            allocated_discounts = []
            if effective_discount > Decimal("0.00") and order_items_gross > Decimal("0.00"):
                discount_paisa = int((effective_discount * 100).to_integral_value())
                line_gross_paisa = [
                    int((line.line_subtotal * 100).to_integral_value()) for line in order_lines
                ]
                total_gross_paisa = sum(line_gross_paisa)

                if total_gross_paisa <= 0 or discount_paisa <= 0:
                    allocated_discounts = [Decimal("0.00")] * len(order_lines)
                else:
                    discount_paisa = min(discount_paisa, total_gross_paisa)
                    allocated_paisa = []
                    remainders = []
                    for idx, g_paisa in enumerate(line_gross_paisa):
                        num = discount_paisa * g_paisa
                        base = num // total_gross_paisa
                        rem = num % total_gross_paisa
                        allocated_paisa.append(base)
                        remainders.append((rem, g_paisa, -idx, idx))

                    remainder_paisa = discount_paisa - sum(allocated_paisa)
                    # Distribute remainder paisa to lines with largest fractional share
                    # Tie-breakers: higher line gross, then earlier index
                    remainders.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
                    for i in range(remainder_paisa):
                        idx = remainders[i][3]
                        allocated_paisa[idx] += 1

                    # Safety check: ensure 0 <= disc <= gross
                    for idx in range(len(allocated_paisa)):
                        allocated_paisa[idx] = min(allocated_paisa[idx], line_gross_paisa[idx])
                        allocated_paisa[idx] = max(0, allocated_paisa[idx])

                    allocated_discounts = [Decimal(p) / Decimal(100) for p in allocated_paisa]
            else:
                allocated_discounts = [Decimal("0.00")] * len(order_lines)

            for line, line_disc in zip(order_lines, allocated_discounts):
                product = getattr(line.variant, "product", None)
                hsn_code = getattr(product, "hsn_code", "") or "0904"
                gst_rate = getattr(product, "gst_rate", None)
                if gst_rate is None or gst_rate <= 0:
                    gst_rate = Decimal("5.00")  # Standard statutory spice rate

                line_gross = line.line_subtotal
                items_subtotal += line_gross
                net_line_total = max(Decimal("0.00"), line_gross - line_disc)

                if net_line_total == Decimal("0.00"):
                    # Zero consideration line (e.g. 100% discount / replacement order)
                    line_taxable = Decimal("0.00")
                    line_tax = Decimal("0.00")
                    half_rate = (gst_rate / Decimal("2.00")).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                    cgst_rate = Decimal("0.00") if is_interstate else half_rate
                    cgst_amount = Decimal("0.00")
                    sgst_rate = Decimal("0.00") if is_interstate else half_rate
                    sgst_amount = Decimal("0.00")
                    igst_rate = gst_rate if is_interstate else Decimal("0.00")
                    igst_amount = Decimal("0.00")
                else:
                    # In Indian e-commerce, MRP/line_subtotal is inclusive of GST
                    # Taxable Value = Net Gross / (1 + (Rate / 100))
                    divisor = Decimal("1.00") + (gst_rate / Decimal("100.00"))
                    line_taxable = (net_line_total / divisor).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                    line_tax = net_line_total - line_taxable
                    taxable_subtotal += line_taxable

                    if is_interstate:
                        cgst_rate = Decimal("0.00")
                        cgst_amount = Decimal("0.00")
                        sgst_rate = Decimal("0.00")
                        sgst_amount = Decimal("0.00")
                        igst_rate = gst_rate
                        igst_amount = line_tax
                        igst_total += igst_amount
                    else:
                        half_rate = (gst_rate / Decimal("2.00")).quantize(
                            Decimal("0.01"), rounding=ROUND_HALF_UP
                        )
                        cgst_rate = half_rate
                        sgst_rate = half_rate
                        cgst_amount = (line_tax / Decimal("2.00")).quantize(
                            Decimal("0.01"), rounding=ROUND_HALF_UP
                        )
                        sgst_amount = line_tax - cgst_amount
                        igst_rate = Decimal("0.00")
                        igst_amount = Decimal("0.00")
                        cgst_total += cgst_amount
                        sgst_total += sgst_amount

                InvoiceLineItem.objects.create(
                    invoice=invoice,
                    order_line_item=line,
                    product_name=line.product_name,
                    variant_name=line.variant_name,
                    sku=line.sku,
                    hsn_code=hsn_code,
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                    discount_amount=line_disc,
                    taxable_amount=line_taxable,
                    gst_rate=gst_rate,
                    cgst_rate=cgst_rate,
                    cgst_amount=cgst_amount,
                    sgst_rate=sgst_rate,
                    sgst_amount=sgst_amount,
                    igst_rate=igst_rate,
                    igst_amount=igst_amount,
                    total_amount=net_line_total,
                )

            total_tax = igst_total if is_interstate else (cgst_total + sgst_total)
            calculated_grand_total = max(
                Decimal("0.00"),
                items_subtotal - effective_discount + locked_order.shipping_fee,
            )

            invoice.items_subtotal = items_subtotal
            invoice.total_discount = effective_discount
            invoice.taxable_subtotal = taxable_subtotal
            invoice.cgst_amount = cgst_total
            invoice.sgst_amount = sgst_total
            invoice.igst_amount = igst_total
            invoice.total_tax = total_tax
            invoice.shipping_fee = locked_order.shipping_fee
            invoice.grand_total = calculated_grand_total
            invoice.save()

            # 10. Generate PDF bytes & attach file
            try:
                cls.regenerate_pdf(invoice)
            except Exception as e:
                logger.warning(f"Deferred PDF rendering for invoice {invoice.invoice_number}: {e}")

            logger.info(
                f"Generated statutory tax invoice {invoice.invoice_number} "
                f"for order {locked_order.order_number}"
            )
            return invoice

    @classmethod
    def regenerate_pdf(cls, invoice: Invoice) -> bytes:
        """
        Regenerates and saves the PDF file for an existing invoice.
        """
        try:
            pdf_bytes = InvoicePDFGenerator.generate(invoice)
            random_token = uuid.uuid4().hex[:12]
            filename = f"Invoice_{invoice.invoice_number.replace('/', '_')}_{random_token}.pdf"
            invoice.pdf_file.save(filename, ContentFile(pdf_bytes), save=False)
            invoice.pdf_generated_at = timezone.now()
            invoice.save(update_fields=["pdf_file", "pdf_generated_at"])
            return pdf_bytes
        except Exception as exc:
            logger.error(
                f"Failed to generate PDF for invoice {invoice.invoice_number}: {exc}",
                exc_info=True,
            )
            raise InvoiceGenerationError(f"Failed to generate invoice PDF: {str(exc)}") from exc
