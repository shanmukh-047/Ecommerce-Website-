"""
Django admin registrations for apps.invoices domain.
"""

from django.contrib import admin

from apps.invoices.models import Invoice, InvoiceLineItem, InvoiceSequence


class InvoiceLineItemInline(admin.TabularInline):
    model = InvoiceLineItem
    extra = 0
    readonly_fields = [
        "product_name",
        "variant_name",
        "sku",
        "hsn_code",
        "quantity",
        "unit_price",
        "taxable_amount",
        "gst_rate",
        "cgst_amount",
        "sgst_amount",
        "igst_amount",
        "total_amount",
    ]
    can_delete = False


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        "invoice_number",
        "order",
        "invoice_date",
        "buyer_name",
        "place_of_supply",
        "is_interstate",
        "is_b2b",
        "grand_total",
        "total_tax",
        "created_at",
    ]
    list_filter = [
        "place_of_supply",
        "is_interstate",
        "is_b2b",
        "invoice_date",
        "created_at",
    ]
    search_fields = [
        "invoice_number",
        "order__order_number",
        "buyer_name",
        "buyer_email",
        "buyer_phone",
        "buyer_company_name",
        "buyer_gstin",
    ]
    readonly_fields = [
        "id",
        "invoice_number",
        "order",
        "invoice_date",
        "seller_name",
        "seller_gstin",
        "seller_fssai",
        "seller_address",
        "seller_state",
        "buyer_name",
        "buyer_email",
        "buyer_phone",
        "buyer_company_name",
        "buyer_gstin",
        "buyer_pan",
        "shipping_address",
        "place_of_supply",
        "is_interstate",
        "is_b2b",
        "items_subtotal",
        "taxable_subtotal",
        "cgst_amount",
        "sgst_amount",
        "igst_amount",
        "total_tax",
        "shipping_fee",
        "grand_total",
        "payment_method",
        "payment_transaction_id",
        "pdf_file",
        "pdf_generated_at",
        "created_at",
        "updated_at",
    ]
    inlines = [InvoiceLineItemInline]


@admin.register(InvoiceSequence)
class InvoiceSequenceAdmin(admin.ModelAdmin):
    list_display = ["financial_year", "last_number"]
    readonly_fields = ["financial_year"]
