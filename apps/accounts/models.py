import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models, transaction
from django.utils import timezone

from apps.core.models import TimeStampedModel

from .managers import UserManager
from .validators import (
    mask_gstin,
    mask_pan,
    normalize_indian_phone,
    validate_gstin,
    validate_indian_phone,
    validate_pan,
    validate_pincode,
)


class Role(models.TextChoices):
    CUSTOMER = "CUSTOMER", "Retail Customer"
    WHOLESALE_PENDING = "WHOLESALE_PENDING", "Wholesale Customer (Pending Verification)"
    WHOLESALE_APPROVED = "WHOLESALE_APPROVED", "Wholesale Customer (Approved)"
    STAFF = "STAFF", "Operations Staff"
    MANAGER = "MANAGER", "Operations Manager"
    SUPERADMIN = "SUPERADMIN", "Super Administrator"


class BusinessType(models.TextChoices):
    RETAILER = "RETAILER", "Retail Store / Supermarket"
    HORECA = "HORECA", "Hotel / Restaurant / Cafe"
    DISTRIBUTOR = "DISTRIBUTOR", "Distributor / Wholesaler"
    OTHER = "OTHER", "Other Enterprise"


class VerificationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending Verification"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"


class AddressType(models.TextChoices):
    HOME = "HOME", "Home"
    WORK = "WORK", "Work / Commercial"
    BILLING = "BILLING", "Billing Office"
    WAREHOUSE = "WAREHOUSE", "Warehouse / Facility"


class IndianStates(models.TextChoices):
    ANDAMAN_AND_NICOBAR = "AN", "Andaman and Nicobar Islands"
    ANDHRA_PRADESH = "AP", "Andhra Pradesh"
    ARUNACHAL_PRADESH = "AR", "Arunachal Pradesh"
    ASSAM = "AS", "Assam"
    BIHAR = "BR", "Bihar"
    CHANDIGARH = "CH", "Chandigarh"
    CHHATTISGARH = "CG", "Chhattisgarh"
    DADRA_AND_NAGAR_HAVELI = "DN", "Dadra and Nagar Haveli and Daman and Diu"
    DELHI = "DL", "Delhi"
    GOA = "GA", "Goa"
    GUJARAT = "GJ", "Gujarat"
    HARYANA = "HR", "Haryana"
    HIMACHAL_PRADESH = "HP", "Himachal Pradesh"
    JAMMU_AND_KASHMIR = "JK", "Jammu and Kashmir"
    JHARKHAND = "JH", "Jharkhand"
    KARNATAKA = "KA", "Karnataka"
    KERALA = "KL", "Kerala"
    LADAKH = "LA", "Ladakh"
    LAKSHADWEEP = "LD", "Lakshadweep"
    MADHYA_PRADESH = "MP", "Madhya Pradesh"
    MAHARASHTRA = "MH", "Maharashtra"
    MANIPUR = "MN", "Manipur"
    MEGHALAYA = "ML", "Meghalaya"
    MIZORAM = "MZ", "Mizoram"
    NAGALAND = "NL", "Nagaland"
    ODISHA = "OD", "Odisha"
    PUDUCHERRY = "PY", "Puducherry"
    PUNJAB = "PB", "Punjab"
    RAJASTHAN = "RJ", "Rajasthan"
    SIKKIM = "SK", "Sikkim"
    TAMIL_NADU = "TN", "Tamil Nadu"
    TELANGANA = "TS", "Telangana"
    TRIPURA = "TR", "Tripura"
    UTTAR_PRADESH = "UP", "Uttar Pradesh"
    UTTARAKHAND = "UK", "Uttarakhand"
    WEST_BENGAL = "WB", "West Bengal"


class User(AbstractBaseUser, PermissionsMixin):
    """
    Primary User model for Bharath Masala Products platform.
    Uses UUID primary keys, normalized lowercase email for authentication,
    and normalized E.164 Indian mobile phone numbers.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    phone_number = models.CharField(
        max_length=15,
        unique=True,
        db_index=True,
        validators=[validate_indian_phone],
    )
    first_name = models.CharField(max_length=60, blank=True)
    last_name = models.CharField(max_length=60, blank=True)
    role = models.CharField(
        max_length=25,
        choices=Role.choices,
        default=Role.CUSTOMER,
        db_index=True,
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["phone_number"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"

    def clean(self):
        super().clean()
        if self.email:
            self.email = self.email.strip().lower()
        if self.phone_number:
            self.phone_number = normalize_indian_phone(self.phone_number)

        # Privilege synchronisation safeguard
        if self.role == Role.SUPERADMIN:
            self.is_superuser = True
            self.is_staff = True
        elif self.role in [Role.MANAGER, Role.STAFF]:
            self.is_staff = True

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def get_full_name(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.email

    @property
    def is_wholesale_buyer(self) -> bool:
        return (
            self.role == Role.WHOLESALE_APPROVED
            and hasattr(self, "wholesale_profile")
            and self.wholesale_profile.verification_status == VerificationStatus.APPROVED
        )


class WholesaleProfile(TimeStampedModel):
    """
    B2B Wholesale account profile with Indian tax/business KYC details
    and verification workflow.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="wholesale_profile",
    )
    company_name = models.CharField(max_length=200)
    gstin = models.CharField(
        max_length=15,
        db_index=True,
        validators=[validate_gstin],
    )
    pan_number = models.CharField(
        max_length=10,
        db_index=True,
        validators=[validate_pan],
    )
    fssai_license = models.CharField(max_length=14, blank=True, default="")
    business_type = models.CharField(
        max_length=30,
        choices=BusinessType.choices,
        default=BusinessType.RETAILER,
    )
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
        db_index=True,
    )
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_wholesale_profiles",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Wholesale Profile"
        verbose_name_plural = "Wholesale Profiles"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.company_name} ({self.get_verification_status_display()})"

    def clean(self):
        super().clean()
        if self.gstin:
            self.gstin = self.gstin.strip().upper()
        if self.pan_number:
            self.pan_number = self.pan_number.strip().upper()

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    @property
    def is_approved(self) -> bool:
        return self.verification_status == VerificationStatus.APPROVED

    @property
    def masked_gstin(self) -> str:
        return mask_gstin(self.gstin)

    @property
    def masked_pan(self) -> str:
        return mask_pan(self.pan_number)


class Address(TimeStampedModel):
    """
    Saved Customer / Wholesale addresses with validation for Indian States,
    Pincode, and guaranteed single default shipping/billing addresses per user.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="addresses",
    )
    recipient_name = models.CharField(max_length=100)
    phone_number = models.CharField(
        max_length=15,
        validators=[validate_indian_phone],
    )
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True, default="")
    landmark = models.CharField(max_length=100, blank=True, default="")
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=50, choices=IndianStates.choices)
    pincode = models.CharField(max_length=6, validators=[validate_pincode])
    address_type = models.CharField(
        max_length=20,
        choices=AddressType.choices,
        default=AddressType.HOME,
    )
    is_default_shipping = models.BooleanField(default=False)
    is_default_billing = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Address"
        verbose_name_plural = "Addresses"
        ordering = ["-is_default_shipping", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default_shipping=True),
                name="unique_default_shipping_per_user",
            ),
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default_billing=True),
                name="unique_default_billing_per_user",
            ),
        ]

    def __str__(self):
        return f"{self.recipient_name}, {self.city}, {self.get_state_display()} - {self.pincode}"

    def clean(self):
        super().clean()
        if self.phone_number:
            self.phone_number = normalize_indian_phone(self.phone_number)
        if self.pincode:
            self.pincode = str(self.pincode).strip()

    def save(self, *args, **kwargs):
        self.clean()
        with transaction.atomic():
            if self.is_default_shipping:
                Address.objects.filter(user=self.user, is_default_shipping=True).exclude(
                    pk=self.pk
                ).update(is_default_shipping=False)
            if self.is_default_billing:
                Address.objects.filter(user=self.user, is_default_billing=True).exclude(
                    pk=self.pk
                ).update(is_default_billing=False)
            super().save(*args, **kwargs)
