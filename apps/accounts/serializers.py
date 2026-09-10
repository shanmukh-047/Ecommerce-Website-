from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed

from .models import Address, User, WholesaleProfile
from .validators import (
    normalize_indian_phone,
    validate_gstin,
    validate_indian_phone,
    validate_pan,
    validate_pincode,
)


class CustomerRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for retail customer self-registration."""

    password = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )
    confirm_password = serializers.CharField(
        write_only=True, required=False, default="", allow_blank=True, style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "phone_number",
            "first_name",
            "last_name",
            "password",
            "confirm_password",
        ]
        read_only_fields = ["id"]

    def validate_email(self, value):
        normalized = value.strip().lower()
        if User.objects.filter(email=normalized).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return normalized

    def validate_phone_number(self, value):
        normalized = normalize_indian_phone(value)
        if User.objects.filter(phone_number=normalized).exists():
            raise serializers.ValidationError("An account with this mobile number already exists.")
        return normalized

    def validate(self, attrs):
        confirm = attrs.get("confirm_password")
        if confirm and attrs["password"] != confirm:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        validate_password(attrs["password"])
        attrs.pop("confirm_password", None)
        return attrs


class WholesaleUserDetailSerializer(serializers.Serializer):
    """User profile data for wholesale registration."""

    email = serializers.EmailField()
    phone_number = serializers.CharField(validators=[validate_indian_phone])
    first_name = serializers.CharField(max_length=60, required=False, allow_blank=True, default="")
    last_name = serializers.CharField(max_length=60, required=False, allow_blank=True, default="")
    password = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )
    confirm_password = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )

    def validate_email(self, value):
        normalized = value.strip().lower()
        if User.objects.filter(email=normalized).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return normalized

    def validate_phone_number(self, value):
        normalized = normalize_indian_phone(value)
        if User.objects.filter(phone_number=normalized).exists():
            raise serializers.ValidationError("An account with this mobile number already exists.")
        return normalized

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        validate_password(attrs["password"])
        attrs.pop("confirm_password")
        return attrs


class WholesaleRegistrationSerializer(serializers.Serializer):
    """Serializer for B2B Wholesale application registration."""

    user = WholesaleUserDetailSerializer()
    company_name = serializers.CharField(max_length=200)
    gstin = serializers.CharField(max_length=15, validators=[validate_gstin])
    pan_number = serializers.CharField(max_length=10, validators=[validate_pan])
    fssai_license = serializers.CharField(
        max_length=14, required=False, allow_blank=True, default=""
    )
    business_type = serializers.ChoiceField(
        choices=WholesaleProfile._meta.get_field("business_type").choices
    )


class LoginSerializer(serializers.Serializer):
    """Secure authentication serializer."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate(self, attrs):
        email = attrs.get("email", "").strip().lower()
        password = attrs.get("password")

        user = authenticate(username=email, password=password)
        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_active:
            raise serializers.ValidationError("This account has been deactivated.")

        attrs["user"] = user
        return attrs


class WholesaleProfileSerializer(serializers.ModelSerializer):
    """Read serializer for Wholesale Profile with masked PII."""

    masked_gstin = serializers.CharField(read_only=True)
    masked_pan = serializers.CharField(read_only=True)

    class Meta:
        model = WholesaleProfile
        fields = [
            "id",
            "company_name",
            "masked_gstin",
            "masked_pan",
            "fssai_license",
            "business_type",
            "verification_status",
            "verified_at",
            "rejection_reason",
            "created_at",
        ]
        read_only_fields = fields


class UserSerializer(serializers.ModelSerializer):
    """User profile serializer for /api/v1/auth/me/"""

    wholesale_profile = WholesaleProfileSerializer(read_only=True)
    is_wholesale_buyer = serializers.BooleanField(read_only=True)
    full_name = serializers.CharField(source="get_full_name", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "phone_number",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "is_staff",
            "is_superuser",
            "is_wholesale_buyer",
            "date_joined",
            "wholesale_profile",
        ]
        read_only_fields = fields


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer allowing users to update self-editable profile fields."""

    class Meta:
        model = User
        fields = ["first_name", "last_name"]


class AddressSerializer(serializers.ModelSerializer):
    """Serializer for user Address Book."""

    phone_number = serializers.CharField(validators=[validate_indian_phone])
    pincode = serializers.CharField(validators=[validate_pincode])

    class Meta:
        model = Address
        fields = [
            "id",
            "recipient_name",
            "phone_number",
            "address_line_1",
            "address_line_2",
            "landmark",
            "city",
            "state",
            "pincode",
            "address_type",
            "is_default_shipping",
            "is_default_billing",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["user"] = user
        return super().create(validated_data)


class WholesaleVerificationSerializer(serializers.Serializer):
    """Serializer for staff/manager wholesale verification decision."""

    action = serializers.ChoiceField(choices=["APPROVE", "REJECT"])
    rejection_reason = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if attrs["action"] == "REJECT" and not attrs.get("rejection_reason", "").strip():
            raise serializers.ValidationError(
                {"rejection_reason": "A reason is mandatory when rejecting a profile."}
            )
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer validating email for one-time password reset request."""

    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer validating token, UID, and new password."""

    uid = serializers.CharField(required=True)
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=False,
        style={"input_type": "password"},
    )

    def validate(self, attrs):
        confirm = attrs.get("confirm_password")
        if confirm and attrs["new_password"] != confirm:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        validate_password(attrs["new_password"])
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer allowing authenticated user to change password."""

    current_password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
    )
    new_password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=False,
        style={"input_type": "password"},
    )

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        if not user or not user.is_authenticated:
            raise serializers.ValidationError("Authentication required to change password.")

        if not user.check_password(attrs["current_password"]):
            raise serializers.ValidationError(
                {"current_password": "The current password you entered is incorrect."}
            )

        confirm = attrs.get("confirm_password")
        if confirm and attrs["new_password"] != confirm:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})

        if attrs["current_password"] == attrs["new_password"]:
            raise serializers.ValidationError(
                {"new_password": "Your new password cannot be identical to your current password."}
            )

        validate_password(attrs["new_password"], user=user)
        return attrs

