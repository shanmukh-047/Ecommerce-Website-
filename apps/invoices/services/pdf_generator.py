"""
Zero-dependency PDF generation service for Bharath Masala statutory GST tax invoices.

Generates strictly compliant standard PDF 1.4 byte streams without external
third-party dependencies (e.g. reportlab, weasyprint).
"""

import io
from decimal import Decimal


def _escape_pdf_text(text: str) -> str:
    """
    Escape special characters for PDF text string literals in Type1 fonts.
    Replaces unicode currency symbol ₹ with 'Rs. ' since Type1 Helvetica
    uses Standard/WinAnsi encoding.
    """
    if not text:
        return ""
    text = str(text)
    text = text.replace("₹", "Rs. ")
    # Replace common unicode dashes/quotes if any
    text = text.replace("—", "-").replace("–", "-")
    text = text.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")

    # Escape PDF literal special characters: \, (, )
    text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    # Strip non-ascii safe
    return "".join(c if ord(c) < 128 else " " for c in text)


class MinimalPDFWriter:
    """
    Generates standard, strictly valid PDF 1.4 documents from basic drawing primitives.
    Page geometry: A4 (595.28 x 841.89 points, standard 72 DPI).
    Coordinates: origin (0, 0) at bottom-left.
    """

    def __init__(self, page_width: float = 595.28, page_height: float = 841.89):
        self.page_width = page_width
        self.page_height = page_height
        self.stream = io.StringIO()

    def set_font(self, font_name: str, size: float):
        """Set font name (F1=Helvetica, F2=Helvetica-Bold) and size in points."""
        self.stream.write(f"/{font_name} {size:.2f} Tf\n")

    def set_text_color(self, r: float, g: float, b: float):
        """Set fill color for text (0.0 to 1.0)."""
        self.stream.write(f"{r:.3f} {g:.3f} {b:.3f} rg\n")

    def set_stroke_color(self, r: float, g: float, b: float):
        """Set stroke color for lines and rects (0.0 to 1.0)."""
        self.stream.write(f"{r:.3f} {g:.3f} {b:.3f} RG\n")

    def set_line_width(self, width: float):
        """Set stroke line width."""
        self.stream.write(f"{width:.2f} w\n")

    def draw_text(self, text: str, x: float, y: float):
        """Draw text string at coordinate (x, y)."""
        escaped = _escape_pdf_text(text)
        self.stream.write(f"BT {x:.2f} {y:.2f} Td ({escaped}) Tj ET\n")

    def draw_text_right_aligned(
        self, text: str, x_right: float, y: float, font_name: str, font_size: float
    ):
        """
        Approximate right-aligned text rendering based on average glyph widths.
        Average Helvetica glyph is ~0.52 * font_size.
        """
        escaped = _escape_pdf_text(text)
        approx_width = len(escaped) * (font_size * 0.52)
        x = max(0.0, x_right - approx_width)
        self.stream.write(f"BT {x:.2f} {y:.2f} Td ({escaped}) Tj ET\n")

    def draw_rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        fill: bool = False,
        stroke: bool = True,
    ):
        """Draw rectangle at (x, y) with given width and height."""
        self.stream.write(f"{x:.2f} {y:.2f} {width:.2f} {height:.2f} re ")
        if fill and stroke:
            self.stream.write("B\n")
        elif fill:
            self.stream.write("f\n")
        elif stroke:
            self.stream.write("S\n")
        else:
            self.stream.write("n\n")

    def draw_line(self, x1: float, y1: float, x2: float, y2: float):
        """Draw a straight line from (x1, y1) to (x2, y2)."""
        self.stream.write(f"{x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S\n")

    def compile_pdf(self) -> bytes:
        """
        Compiles the drawing stream into a complete, conforming PDF 1.4 binary document.
        """
        content = self.stream.getvalue().encode("latin-1")
        content_length = len(content)

        # Build PDF objects with byte offsets
        objects = []
        body = io.BytesIO()

        def add_object(obj_bytes: bytes) -> int:
            offset = body.tell()
            objects.append(offset)
            body.write(obj_bytes)
            return len(objects)

        # 1. Catalog
        add_object(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")

        # 2. Pages
        add_object(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")

        # 3. Page
        add_object(
            f"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.page_width:.2f} {self.page_height:.2f}] "
            f"/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>\nendobj\n".encode(
                "latin-1"
            )
        )

        # 4. Font F1 (Helvetica Regular)
        add_object(
            b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>\nendobj\n"
        )

        # 5. Font F2 (Helvetica Bold)
        add_object(
            b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>\nendobj\n"
        )

        # 6. Stream Contents
        stream_obj = (
            f"6 0 obj\n<< /Length {content_length} >>\nstream\n".encode("latin-1")
            + content
            + b"\nendstream\nendobj\n"
        )
        add_object(stream_obj)

        # Assemble document
        output = io.BytesIO()
        output.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        header_len = output.tell()

        # Adjust offsets by header_len
        body_bytes = body.getvalue()
        output.write(body_bytes)

        xref_offset = output.tell()
        output.write(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
        output.write(b"0000000000 65535 f \n")
        for offset in objects:
            output.write(f"{offset + header_len:010d} 00000 n \n".encode("latin-1"))

        trailer = (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("latin-1")
        output.write(trailer)

        return output.getvalue()


class InvoicePDFGenerator:
    """
    Renders statutory GST Tax Invoice details into a clean A4 PDF layout.
    """

    @classmethod
    def generate(cls, invoice) -> bytes:
        writer = MinimalPDFWriter()
        pw = writer.page_width
        ph = writer.page_height
        margin = 36.0  # 0.5 inch margins

        # Background header band
        writer.set_fill_color_hex = lambda: None
        writer.set_stroke_color(0.8, 0.2, 0.2)  # Brand maroon
        writer.set_line_width(1.5)
        writer.draw_line(margin, ph - 40, pw - margin, ph - 40)

        # Header Title
        writer.set_font("F2", 18)
        writer.set_text_color(0.65, 0.1, 0.1)  # Deep Crimson / Maroon
        writer.draw_text("TAX INVOICE", margin, ph - 30)

        writer.set_font("F2", 9)
        writer.set_text_color(0.3, 0.3, 0.3)
        writer.draw_text_right_aligned("ORIGINAL FOR RECIPIENT", pw - margin, ph - 30, "F2", 9)

        # Seller Information (Left side)
        y = ph - 60
        writer.set_font("F2", 13)
        writer.set_text_color(0.1, 0.1, 0.1)
        writer.draw_text(invoice.seller_name, margin, y)

        writer.set_font("F1", 8.5)
        writer.set_text_color(0.25, 0.25, 0.25)
        y -= 13
        writer.draw_text(invoice.seller_address[:65], margin, y)
        if len(invoice.seller_address) > 65:
            y -= 11
            writer.draw_text(invoice.seller_address[65:130], margin, y)
        y -= 13
        writer.draw_text(
            f"GSTIN: {invoice.seller_gstin}   |   FSSAI: {invoice.seller_fssai}   |   State: {invoice.seller_state} (29)",
            margin,
            y,
        )

        # Invoice Meta Box (Right Side)
        meta_x = pw - margin - 220
        meta_y = ph - 55
        writer.set_stroke_color(0.85, 0.85, 0.85)
        writer.set_line_width(0.75)
        writer.draw_rect(meta_x, meta_y - 50, 220, 52, fill=False, stroke=True)

        writer.set_font("F2", 8.5)
        writer.set_text_color(0.1, 0.1, 0.1)
        writer.draw_text(f"Invoice No:  {invoice.invoice_number}", meta_x + 8, meta_y - 14)
        writer.draw_text(
            f"Invoice Date: {invoice.invoice_date.strftime('%d-%m-%Y')}", meta_x + 8, meta_y - 26
        )
        writer.draw_text(f"Order No:    {invoice.order.order_number}", meta_x + 8, meta_y - 38)
        writer.draw_text(f"Place of Supply: {invoice.place_of_supply}", meta_x + 8, meta_y - 48)

        # Divider
        y -= 18
        writer.set_stroke_color(0.7, 0.7, 0.7)
        writer.set_line_width(0.5)
        writer.draw_line(margin, y, pw - margin, y)

        # Buyer & Consignee Box
        y -= 12
        box_width = (pw - (margin * 2) - 10) / 2
        box_height = 70.0
        box_y = y - box_height

        # Billed To Box
        writer.set_stroke_color(0.85, 0.85, 0.85)
        writer.draw_rect(margin, box_y, box_width, box_height, fill=False, stroke=True)

        writer.set_font("F2", 9)
        writer.set_text_color(0.2, 0.2, 0.2)
        writer.draw_text("BILLED TO / BUYER DETAILS", margin + 8, y - 13)

        writer.set_font("F1", 8.5)
        writer.set_text_color(0.2, 0.2, 0.2)
        b_name = (
            invoice.buyer_company_name
            if invoice.is_b2b and invoice.buyer_company_name
            else invoice.buyer_name
        )
        writer.draw_text(f"Name: {b_name[:36]}", margin + 8, y - 25)
        writer.draw_text(
            f"Phone: {invoice.buyer_phone}   Email: {invoice.buyer_email[:22]}", margin + 8, y - 37
        )
        if invoice.is_b2b:
            writer.draw_text(
                f"GSTIN: {invoice.buyer_gstin or 'N/A'}   PAN: {invoice.buyer_pan or 'N/A'}",
                margin + 8,
                y - 49,
            )
            writer.draw_text("Type: Wholesale (B2B)", margin + 8, y - 61)
        else:
            writer.draw_text("Type: Retail Consumer (B2C)", margin + 8, y - 49)
            writer.draw_text(f"State: {invoice.place_of_supply}", margin + 8, y - 61)

        # Shipped To Box
        ship_x = margin + box_width + 10
        writer.draw_rect(ship_x, box_y, box_width, box_height, fill=False, stroke=True)

        writer.set_font("F2", 9)
        writer.set_text_color(0.2, 0.2, 0.2)
        writer.draw_text("SHIPPED TO / DELIVERY ADDRESS", ship_x + 8, y - 13)

        writer.set_font("F1", 8.5)
        addr_lines = invoice.shipping_address.replace("\n", ", ").split(", ")
        line1 = ", ".join(addr_lines[:3])[:42]
        line2 = ", ".join(addr_lines[3:6])[:42]
        writer.draw_text(line1, ship_x + 8, y - 27)
        if line2:
            writer.draw_text(line2, ship_x + 8, y - 39)
        writer.draw_text(f"State: {invoice.place_of_supply}", ship_x + 8, y - 51)
        writer.draw_text(
            f"Inter-State Supply: {'YES (IGST)' if invoice.is_interstate else 'NO (CGST + SGST)'}",
            ship_x + 8,
            y - 63,
        )

        # Items Table
        table_top = box_y - 20
        writer.set_stroke_color(0.4, 0.4, 0.4)
        writer.set_line_width(1.0)
        writer.draw_line(margin, table_top, pw - margin, table_top)

        # Table Column Positions:
        # Col 0: SKU & Description (x=margin to 215)
        # Col 1: HSN (220 to 260)
        # Col 2: Qty (265 to 295)
        # Col 3: Unit Price (300 to 345)
        # Col 4: Taxable Val (350 to 405)
        # Col 5: GST% (410 to 445)
        # Col 6: Tax Amt (450 to 495)
        # Col 7: Total (500 to pw-margin)
        writer.set_font("F2", 8)
        writer.set_text_color(0.1, 0.1, 0.1)
        th_y = table_top - 12
        writer.draw_text("Item Description / SKU", margin + 4, th_y)
        writer.draw_text("HSN", 215, th_y)
        writer.draw_text("Qty", 258, th_y)
        writer.draw_text("Rate", 295, th_y)
        writer.draw_text("Taxable", 345, th_y)
        writer.draw_text("GST%", 400, th_y)
        writer.draw_text("Tax Amt", 445, th_y)
        writer.draw_text("Total (Rs)", pw - margin - 48, th_y)

        writer.set_line_width(0.5)
        writer.set_stroke_color(0.7, 0.7, 0.7)
        writer.draw_line(margin, th_y - 6, pw - margin, th_y - 6)

        # Table Rows
        row_y = th_y - 18
        writer.set_font("F1", 7.8)
        lines = list(invoice.lines.all())

        for line in lines:
            if row_y < 160:  # Bottom margin guard
                break
            desc = f"{line.product_name} - {line.variant_name}"
            writer.draw_text(desc[:34], margin + 4, row_y)
            writer.draw_text(line.hsn_code, 215, row_y)
            writer.draw_text(str(line.quantity), 260, row_y)
            writer.draw_text(f"{line.unit_price:.2f}", 292, row_y)
            writer.draw_text(f"{line.taxable_amount:.2f}", 342, row_y)
            writer.draw_text(f"{line.gst_rate:.1f}%", 402, row_y)

            tax_amt = (
                line.igst_amount if invoice.is_interstate else (line.cgst_amount + line.sgst_amount)
            )
            writer.draw_text(f"{tax_amt:.2f}", 445, row_y)
            writer.draw_text_right_aligned(
                f"{line.total_amount:.2f}", pw - margin - 4, row_y, "F1", 7.8
            )

            row_y -= 14

        # Divider above totals
        writer.set_line_width(0.75)
        writer.set_stroke_color(0.5, 0.5, 0.5)
        writer.draw_line(margin, row_y, pw - margin, row_y)

        # Totals Section (Right Aligned block)
        tot_x_label = pw - margin - 190
        tot_x_val = pw - margin - 4
        ty = row_y - 14

        writer.set_font("F1", 8.5)
        writer.draw_text("Gross Subtotal:", tot_x_label, ty)
        writer.draw_text_right_aligned(
            f"Rs. {invoice.items_subtotal:.2f}", tot_x_val, ty, "F1", 8.5
        )
        ty -= 12

        if getattr(invoice, "total_discount", Decimal("0.00")) > Decimal("0.00"):
            writer.draw_text("Order Discount:", tot_x_label, ty)
            writer.draw_text_right_aligned(
                f"- Rs. {invoice.total_discount:.2f}", tot_x_val, ty, "F1", 8.5
            )
            ty -= 12

        writer.draw_text("Taxable Subtotal:", tot_x_label, ty)
        writer.draw_text_right_aligned(
            f"Rs. {invoice.taxable_subtotal:.2f}", tot_x_val, ty, "F1", 8.5
        )
        ty -= 12

        if invoice.grand_total == Decimal("0.00") and getattr(
            invoice, "total_discount", Decimal("0.00")
        ) > Decimal("0.00"):
            writer.set_font("F2", 8)
            writer.set_text_color(0.5, 0.1, 0.1)
            writer.draw_text("NOTE: ZERO-VALUE REPLACEMENT", margin + 4, ty + 12)
            writer.set_font("F1", 7.5)
            writer.set_text_color(0.3, 0.3, 0.3)
            writer.draw_text(
                "(Warranty/Return Fulfillment - No Consideration Payable)", margin + 4, ty
            )

        if invoice.is_interstate:
            writer.draw_text("Integrated GST (IGST):", tot_x_label, ty)
            writer.draw_text_right_aligned(
                f"Rs. {invoice.igst_amount:.2f}", tot_x_val, ty, "F1", 8.5
            )
            ty -= 12
        else:
            writer.draw_text("Central GST (CGST):", tot_x_label, ty)
            writer.draw_text_right_aligned(
                f"Rs. {invoice.cgst_amount:.2f}", tot_x_val, ty, "F1", 8.5
            )
            ty -= 12
            writer.draw_text("State GST (SGST):", tot_x_label, ty)
            writer.draw_text_right_aligned(
                f"Rs. {invoice.sgst_amount:.2f}", tot_x_val, ty, "F1", 8.5
            )
            ty -= 12

        if invoice.shipping_fee > 0:
            writer.draw_text("Shipping & Handling:", tot_x_label, ty)
            writer.draw_text_right_aligned(
                f"Rs. {invoice.shipping_fee:.2f}", tot_x_val, ty, "F1", 8.5
            )
            ty -= 12

        # Grand Total Box
        ty -= 4
        writer.set_stroke_color(0.65, 0.1, 0.1)
        writer.set_line_width(1.0)
        writer.draw_rect(tot_x_label - 6, ty - 8, 200, 22, fill=False, stroke=True)

        writer.set_font("F2", 10.5)
        writer.set_text_color(0.65, 0.1, 0.1)
        writer.draw_text("GRAND TOTAL:", tot_x_label, ty + 2)
        writer.draw_text_right_aligned(
            f"Rs. {invoice.grand_total:.2f}", tot_x_val, ty + 2, "F2", 10.5
        )

        # Statutory Declaration & Signature (Bottom)
        decl_y = 75
        writer.set_font("F2", 8)
        writer.set_text_color(0.2, 0.2, 0.2)
        writer.draw_text("Statutory Declaration:", margin, decl_y)

        writer.set_font("F1", 7.5)
        writer.set_text_color(0.35, 0.35, 0.35)
        writer.draw_text(
            "We declare that this invoice shows the actual price of the goods described and that all particulars are true and correct.",
            margin,
            decl_y - 11,
        )
        writer.draw_text(
            "Goods once sold are covered under standard quality warranty as per FSSAI regulations.",
            margin,
            decl_y - 21,
        )

        # Signatory block (Right)
        sig_x = pw - margin - 170
        writer.set_font("F2", 8)
        writer.set_text_color(0.1, 0.1, 0.1)
        writer.draw_text(f"For {invoice.seller_name[:26]}", sig_x, decl_y)
        writer.draw_line(sig_x, decl_y - 25, pw - margin, decl_y - 25)
        writer.set_font("F1", 7.5)
        writer.draw_text("Authorised Signatory", sig_x + 25, decl_y - 35)

        return writer.compile_pdf()
