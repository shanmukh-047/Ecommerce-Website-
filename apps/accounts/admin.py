from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Address, User, WholesaleProfile


class WholesaleProfileInline(admin.StackedInline):
    model = WholesaleProfile
    fk_name = "user"
    can_delete = False
    verbose_name_plural = "Wholesale Profile"
    readonly_fields = ["created_at", "updated_at", "verified_at", "verified_by"]
    fields = [
        "company_name",
        "business_type",
        "gstin",
        "pan_number",
        "fssai_license",
        "verification_status",
        "verified_by",
        "verified_at",
        "rejection_reason",
    ]


class AddressInline(admin.TabularInline):
    model = Address
    extra = 0
    fields = [
        "recipient_name",
        "phone_number",
        "city",
        "state",
        "pincode",
        "address_type",
        "is_default_shipping",
        "is_default_billing",
    ]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for custom User model."""

    list_display = [
        "email",
        "phone_number",
        "first_name",
        "last_name",
        "role",
        "is_active",
        "date_joined",
    ]
    list_filter = ["role", "is_active", "is_staff", "is_superuser", "date_joined"]
    search_fields = ["email", "phone_number", "first_name", "last_name"]
    ordering = ["-date_joined"]
    readonly_fields = ["id", "date_joined", "last_login"]
    inlines = [WholesaleProfileInline, AddressInline]

    fieldsets = (
        (None, {"fields": ("id", "email", "phone_number", "password")}),
        ("Personal Info", {"fields": ("first_name", "last_name")}),
        (
            "Permissions & Roles",
            {
                "fields": (
                    "role",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "phone_number", "password", "confirm_password", "role"),
            },
        ),
    )


@admin.register(WholesaleProfile)
class WholesaleProfileAdmin(admin.ModelAdmin):
    """Admin interface for B2B Wholesale Profiles and KYC verification."""

    list_display = [
        "company_name",
        "user_email",
        "business_type",
        "verification_status",
        "masked_pan",
        "masked_gstin",
        "verified_by",
        "verified_at",
    ]
    list_filter = ["verification_status", "business_type", "created_at"]
    search_fields = ["company_name", "gstin", "pan_number", "user__email", "user__phone_number"]
    readonly_fields = ["id", "created_at", "updated_at", "verified_at", "verified_by"]
    fields = [
        "id",
        "user",
        "company_name",
        "business_type",
        "gstin",
        "pan_number",
        "fssai_license",
        "verification_status",
        "verified_by",
        "verified_at",
        "rejection_reason",
        "created_at",
        "updated_at",
    ]

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = "User Email"


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    """Admin interface for Customer Addresses."""

    list_display = [
        "recipient_name",
        "user_email",
        "city",
        "state",
        "pincode",
        "address_type",
        "is_default_shipping",
        "is_default_billing",
    ]
    list_filter = ["state", "address_type", "is_default_shipping", "is_default_billing"]
    search_fields = ["recipient_name", "phone_number", "city", "pincode", "user__email"]
    readonly_fields = ["id", "created_at", "updated_at"]

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = "User Email"
