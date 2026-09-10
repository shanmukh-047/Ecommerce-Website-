"""
DRF Serializers for statutory GST invoices.
"""

from rest_framework import serializers

from apps.invoices.models import CreditNote, CreditNoteLine, Invoice, InvoiceLineItem


class InvoiceLineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLineItem
        fields = [
            "id",
            "product_name",
            "variant_name",
            "sku",
            "hsn_code",
            "quantity",
            "unit_price",
            "discount_amount",
            "taxable_amount",
            "gst_rate",
            "cgst_rate",
            "cgst_amount",
            "sgst_rate",
            "sgst_amount",
            "igst_rate",
            "igst_amount",
            "total_amount",
        ]
        read_only_fields = fields


class InvoiceSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source="order.order_number", read_only=True)
    lines = InvoiceLineItemSerializer(many=True, read_only=True)
    download_url = serializers.SerializerMethodField()
    html_url = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            "id",
            "invoice_number",
            "status",
            "order",
            "order_number",
            "invoice_date",
            # Seller
            "seller_name",
            "seller_gstin",
            "seller_fssai",
            "seller_address",
            "seller_state",
            # Buyer
            "buyer_name",
            "buyer_email",
            "buyer_phone",
            "buyer_company_name",
            "buyer_gstin",
            "buyer_pan",
            "shipping_address",
            # Tax breakdown
            "place_of_supply",
            "is_interstate",
            "is_b2b",
            "items_subtotal",
            "total_discount",
            "taxable_subtotal",
            "cgst_amount",
            "sgst_amount",
            "igst_amount",
            "total_tax",
            "shipping_fee",
            "grand_total",
            "payment_method",
            "payment_transaction_id",
            "pdf_generated_at",
            "download_url",
            "html_url",
            "lines",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_download_url(self, obj) -> str:
        request = self.context.get("request")
        url = f"/api/v1/orders/{obj.order_id}/invoice/download/"
        return request.build_absolute_uri(url) if request else url

    def get_html_url(self, obj) -> str:
        request = self.context.get("request")
        url = f"/api/v1/orders/{obj.order_id}/invoice/html/"
        return request.build_absolute_uri(url) if request else url


class CreditNoteLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditNoteLine
        fields = [
            "id",
            "product_name",
            "variant_name",
            "sku",
            "hsn_code",
            "quantity",
            "unit_price",
            "taxable_amount",
            "gst_rate",
            "cgst_rate",
            "cgst_amount",
            "sgst_rate",
            "sgst_amount",
            "igst_rate",
            "igst_amount",
            "total_amount",
        ]
        read_only_fields = fields


class CreditNoteSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source="order.order_number", read_only=True)
    original_invoice_number = serializers.CharField(
        source="original_invoice.invoice_number", read_only=True
    )
    lines = CreditNoteLineSerializer(many=True, read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = CreditNote
        fields = [
            "id",
            "credit_note_number",
            "original_invoice",
            "original_invoice_number",
            "order",
            "order_number",
            "credit_note_date",
            "financial_year",
            "reason",
            "reason_notes",
            # Seller
            "seller_name",
            "seller_gstin",
            "seller_fssai",
            "seller_address",
            "seller_state",
            # Buyer
            "buyer_name",
            "buyer_email",
            "buyer_phone",
            "buyer_company_name",
            "buyer_gstin",
            "buyer_pan",
            "shipping_address",
            # Tax breakdown
            "place_of_supply",
            "is_interstate",
            "is_b2b",
            "items_subtotal",
            "taxable_subtotal",
            "cgst_amount",
            "sgst_amount",
            "igst_amount",
            "total_tax",
            "grand_total",
            "pdf_generated_at",
            "download_url",
            "lines",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_download_url(self, obj) -> str:
        request = self.context.get("request")
        url = f"/api/v1/orders/{obj.order_id}/credit-notes/{obj.id}/download/"
        return request.build_absolute_uri(url) if request else url
