"""
Zero-dependency PDF generation service for Bharath Masala statutory GST Tax Credit Notes.

Generates strictly compliant standard PDF 1.4 byte streams conforming to
Section 34 of the CGST Act, 2017, and Rule 53(1A) of the CGST Rules, 2017.
"""

from apps.invoices.services.pdf_generator import MinimalPDFWriter


class CreditNotePDFGenerator:
    """
    Generates statutory Tax Credit Note PDF conforming to Rule 53(1A).
    Mandatory inclusions:
    - Distinct Document Title: 'TAX CREDIT NOTE'
    - Original Tax Invoice Number and Invoice Date
    - Supplier GSTIN, FSSAI, Legal Address
    - Recipient details (Name, Address, B2B GSTIN/PAN)
    - Itemized tax reversals with HSN and GST rates
    - Reverse CGST/SGST/IGST breakdown
    - Reason for Credit Note issuance
    """

    @classmethod
    def generate(cls, credit_note) -> bytes:
        writer = MinimalPDFWriter()
        pw, ph = writer.page_width, writer.page_height
        margin = 36.0  # 0.5 inch margins

        # Header Title Banner: TAX CREDIT NOTE
        writer.set_fill_color = getattr(writer, "set_text_color", None)
        writer.set_stroke_color(0.65, 0.15, 0.15)  # Maroon/crimson tone
        writer.set_line_width(1.5)
        writer.draw_rect(margin, ph - 42, pw - (margin * 2), 24, fill=False, stroke=True)

        writer.set_font("F2", 11)
        writer.set_text_color(0.65, 0.15, 0.15)
        writer.draw_text("STATUTORY TAX CREDIT NOTE", margin + 12, ph - 34)

        writer.set_font("F1", 7.5)
        writer.set_text_color(0.4, 0.4, 0.4)
        writer.draw_text_right_aligned(
            "(Issued under Section 34 of the CGST Act, 2017 / Rule 53(1A))",
            pw - margin - 12,
            ph - 34,
            "F1",
            7.5,
        )

        # Seller Information (Left side)
        y = ph - 60
        writer.set_font("F2", 12)
        writer.set_text_color(0.1, 0.1, 0.1)
        writer.draw_text(credit_note.seller_name, margin, y)

        writer.set_font("F1", 8.0)
        writer.set_text_color(0.25, 0.25, 0.25)
        y -= 12
        writer.draw_text(credit_note.seller_address[:65], margin, y)
        if len(credit_note.seller_address) > 65:
            y -= 10
            writer.draw_text(credit_note.seller_address[65:130], margin, y)
        y -= 12
        writer.draw_text(
            f"GSTIN: {credit_note.seller_gstin}   |   FSSAI: {credit_note.seller_fssai}   |   State: {credit_note.seller_state} (29)",
            margin,
            y,
        )

        # Credit Note & Original Invoice Meta Box (Right Side)
        meta_x = pw - margin - 230
        meta_y = ph - 52
        writer.set_stroke_color(0.8, 0.8, 0.8)
        writer.set_line_width(0.75)
        writer.draw_rect(meta_x, meta_y - 62, 230, 64, fill=False, stroke=True)

        writer.set_font("F2", 8.5)
        writer.set_text_color(0.1, 0.1, 0.1)
        writer.draw_text(
            f"Credit Note No:   {credit_note.credit_note_number}", meta_x + 8, meta_y - 12
        )
        writer.draw_text(
            f"Credit Note Date: {credit_note.credit_note_date.strftime('%d-%m-%Y')}",
            meta_x + 8,
            meta_y - 24,
        )

        orig_inv = credit_note.original_invoice
        writer.draw_text(
            f"Original Inv No:  {orig_inv.invoice_number}",
            meta_x + 8,
            meta_y - 36,
        )
        writer.draw_text(
            f"Original Inv Date:{orig_inv.invoice_date.strftime('%d-%m-%Y')}",
            meta_x + 8,
            meta_y - 48,
        )
        writer.draw_text(
            f"Reason: {credit_note.get_reason_display()[:28]}",
            meta_x + 8,
            meta_y - 58,
        )

        # Divider
        y -= 16
        writer.set_stroke_color(0.7, 0.7, 0.7)
        writer.set_line_width(0.5)
        writer.draw_line(margin, y, pw - margin, y)

        # Buyer & Reason Box
        y -= 12
        box_width = (pw - (margin * 2) - 10) / 2
        box_height = 68.0
        box_y = y - box_height

        # Recipient Details Box
        writer.set_stroke_color(0.85, 0.85, 0.85)
        writer.draw_rect(margin, box_y, box_width, box_height, fill=False, stroke=True)

        writer.set_font("F2", 8.5)
        writer.set_text_color(0.2, 0.2, 0.2)
        writer.draw_text("CREDIT ISSUED TO / BUYER DETAILS", margin + 8, y - 12)

        writer.set_font("F1", 8.0)
        writer.set_text_color(0.2, 0.2, 0.2)
        b_name = (
            credit_note.buyer_company_name
            if credit_note.is_b2b and credit_note.buyer_company_name
            else credit_note.buyer_name
        )
        writer.draw_text(f"Name: {b_name[:36]}", margin + 8, y - 24)
        writer.draw_text(
            f"Phone: {credit_note.buyer_phone}   Email: {credit_note.buyer_email[:20]}",
            margin + 8,
            y - 36,
        )
        if credit_note.is_b2b:
            writer.draw_text(
                f"GSTIN: {credit_note.buyer_gstin or 'N/A'}   PAN: {credit_note.buyer_pan or 'N/A'}",
                margin + 8,
                y - 48,
            )
            writer.draw_text("Type: Wholesale (B2B)", margin + 8, y - 59)
        else:
            writer.draw_text("Type: Retail Consumer (B2C)", margin + 8, y - 48)
            writer.draw_text(f"State: {credit_note.place_of_supply}", margin + 8, y - 59)

        # Shipping & Reversal Context Box
        ctx_x = margin + box_width + 10
        writer.draw_rect(ctx_x, box_y, box_width, box_height, fill=False, stroke=True)

        writer.set_font("F2", 8.5)
        writer.set_text_color(0.2, 0.2, 0.2)
        writer.draw_text("TAX REVERSAL CONTEXT", ctx_x + 8, y - 12)

        writer.set_font("F1", 8.0)
        writer.draw_text(f"Order Number: {credit_note.order.order_number}", ctx_x + 8, y - 24)
        writer.draw_text(f"Place of Supply: {credit_note.place_of_supply}", ctx_x + 8, y - 36)
        writer.draw_text(
            f"Tax Regime: {'Inter-State (IGST Reversed)' if credit_note.is_interstate else 'Intra-State (CGST + SGST Reversed)'}",
            ctx_x + 8,
            y - 48,
        )
        if credit_note.reason_notes:
            writer.draw_text(f"Notes: {credit_note.reason_notes[:38]}", ctx_x + 8, y - 59)

        # Items Table
        table_top = box_y - 18
        writer.set_stroke_color(0.4, 0.4, 0.4)
        writer.set_line_width(1.0)
        writer.draw_line(margin, table_top, pw - margin, table_top)

        writer.set_font("F2", 8.0)
        writer.set_text_color(0.1, 0.1, 0.1)
        th_y = table_top - 12
        writer.draw_text("Item Description / SKU", margin + 4, th_y)
        writer.draw_text("HSN", 215, th_y)
        writer.draw_text("Qty", 258, th_y)
        writer.draw_text("Rate", 295, th_y)
        writer.draw_text("Taxable", 345, th_y)
        writer.draw_text("GST%", 400, th_y)
        writer.draw_text("Tax Cred", 445, th_y)
        writer.draw_text("Total (Rs)", pw - margin - 48, th_y)

        writer.set_line_width(0.5)
        writer.set_stroke_color(0.7, 0.7, 0.7)
        writer.draw_line(margin, th_y - 6, pw - margin, th_y - 6)

        # Rows
        row_y = th_y - 16
        writer.set_font("F1", 7.8)
        lines = list(credit_note.lines.all())

        for line in lines:
            if row_y < 160:
                break
            desc = f"{line.product_name} - {line.variant_name}"
            writer.draw_text(desc[:34], margin + 4, row_y)
            writer.draw_text(line.hsn_code, 215, row_y)
            writer.draw_text(str(line.quantity), 260, row_y)
            writer.draw_text(f"{line.unit_price:.2f}", 292, row_y)
            writer.draw_text(f"{line.taxable_amount:.2f}", 342, row_y)
            writer.draw_text(f"{line.gst_rate:.1f}%", 402, row_y)

            tax_amt = (
                line.igst_amount
                if credit_note.is_interstate
                else (line.cgst_amount + line.sgst_amount)
            )
            writer.draw_text(f"{tax_amt:.2f}", 445, row_y)
            writer.draw_text_right_aligned(
                f"{line.total_amount:.2f}", pw - margin - 4, row_y, "F1", 7.8
            )
            row_y -= 14

        # Table Bottom Rule
        writer.set_stroke_color(0.7, 0.7, 0.7)
        writer.draw_line(margin, row_y, pw - margin, row_y)

        # Summary Totals Box (Bottom Right)
        totals_y = max(row_y - 12, 140.0)
        tot_box_w = 220.0
        tot_x = pw - margin - tot_box_w

        writer.set_font("F1", 8.0)
        writer.set_text_color(0.2, 0.2, 0.2)

        writer.draw_text("Items Taxable Subtotal:", tot_x, totals_y)
        writer.draw_text_right_aligned(
            f"Rs. {credit_note.taxable_subtotal:.2f}", pw - margin - 4, totals_y, "F1", 8.0
        )

        totals_y -= 12
        if credit_note.is_interstate:
            writer.draw_text("IGST Reversed:", tot_x, totals_y)
            writer.draw_text_right_aligned(
                f"Rs. {credit_note.igst_amount:.2f}", pw - margin - 4, totals_y, "F1", 8.0
            )
        else:
            writer.draw_text("CGST Reversed:", tot_x, totals_y)
            writer.draw_text_right_aligned(
                f"Rs. {credit_note.cgst_amount:.2f}", pw - margin - 4, totals_y, "F1", 8.0
            )
            totals_y -= 12
            writer.draw_text("SGST Reversed:", tot_x, totals_y)
            writer.draw_text_right_aligned(
                f"Rs. {credit_note.sgst_amount:.2f}", pw - margin - 4, totals_y, "F1", 8.0
            )

        totals_y -= 12
        writer.draw_text("Total Tax Credited:", tot_x, totals_y)
        writer.draw_text_right_aligned(
            f"Rs. {credit_note.total_tax:.2f}", pw - margin - 4, totals_y, "F1", 8.0
        )

        totals_y -= 14
        writer.set_stroke_color(0.3, 0.3, 0.3)
        writer.set_line_width(0.75)
        writer.draw_line(tot_x, totals_y + 10, pw - margin, totals_y + 10)

        writer.set_font("F2", 9.5)
        writer.set_text_color(0.65, 0.15, 0.15)
        writer.draw_text("TOTAL AMOUNT CREDITED:", tot_x, totals_y - 2)
        writer.draw_text_right_aligned(
            f"Rs. {credit_note.grand_total:.2f}", pw - margin - 4, totals_y - 2, "F2", 9.5
        )

        # Statutory Declaration & Signature (Bottom Left & Right)
        b_y = 65.0
        writer.set_font("F1", 7.0)
        writer.set_text_color(0.4, 0.4, 0.4)
        writer.draw_text(
            "This document is a formal GST Credit Note issued pursuant to Section 34 of the CGST Act, 2017.",
            margin,
            b_y,
        )
        writer.draw_text(
            "The output tax liability of the supplier stands reduced by the credited tax amounts declared herein.",
            margin,
            b_y - 9,
        )
        writer.draw_text(
            "Registered buyers are required to reverse corresponding Input Tax Credit (ITC) as per statutory GST rules.",
            margin,
            b_y - 18,
        )

        writer.set_font("F2", 7.5)
        writer.set_text_color(0.2, 0.2, 0.2)
        writer.draw_text_right_aligned(
            f"For {credit_note.seller_name}", pw - margin, b_y, "F2", 7.5
        )
        writer.draw_text_right_aligned("Authorized Signatory", pw - margin, b_y - 25, "F1", 7.0)

        return writer.compile_pdf()
