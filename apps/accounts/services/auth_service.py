import logging

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Role, User, VerificationStatus, WholesaleProfile
from apps.accounts.services.email_service import EmailService
from apps.accounts.validators import normalize_indian_phone

logger = logging.getLogger(__name__)


class AuthService:
    """
    Central business service handling user registration, authentication tokens,
    cookie persistence, and wholesale approval lifecycle.
    """

    @staticmethod
    def generate_tokens_for_user(user: User) -> tuple[str, RefreshToken]:
        """Generate a new Access Token and Refresh Token pair."""
        refresh = RefreshToken.for_user(user)
        # Include custom claims if necessary
        refresh["role"] = user.role
        refresh["email"] = user.email
        return str(refresh.access_token), refresh

    @staticmethod
    def set_refresh_cookie(response: HttpResponse, refresh_token: RefreshToken) -> None:
        """
        Store the refresh token in a secure HttpOnly cookie scoped to auth endpoints.
        """
        cookie_name = getattr(settings, "JWT_REFRESH_COOKIE_NAME", "refresh_token")
        cookie_path = getattr(settings, "JWT_REFRESH_COOKIE_PATH", "/api/v1/auth/")
        secure = getattr(settings, "SECURE_COOKIE", False)
        samesite = getattr(settings, "COOKIE_SAMESITE", "Lax")
        domain = getattr(settings, "COOKIE_DOMAIN", None)
        max_age = int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())

        response.set_cookie(
            key=cookie_name,
            value=str(refresh_token),
            max_age=max_age,
            path=cookie_path,
            domain=domain,
            secure=secure,
            httponly=True,
            samesite=samesite,
        )

    @staticmethod
    def clear_refresh_cookie(response: HttpResponse) -> None:
        """Unset and invalidate the refresh token cookie."""
        cookie_name = getattr(settings, "JWT_REFRESH_COOKIE_NAME", "refresh_token")
        cookie_path = getattr(settings, "JWT_REFRESH_COOKIE_PATH", "/api/v1/auth/")
        domain = getattr(settings, "COOKIE_DOMAIN", None)

        response.delete_cookie(
            key=cookie_name,
            path=cookie_path,
            domain=domain,
        )

    @staticmethod
    def register_retail_customer(validated_data: dict) -> User:
        """Create a standard retail customer account."""
        email = validated_data["email"].strip().lower()
        phone_number = normalize_indian_phone(validated_data["phone_number"])
        password = validated_data["password"]
        first_name = validated_data.get("first_name", "").strip()
        last_name = validated_data.get("last_name", "").strip()

        user = User.objects.create_user(
            email=email,
            phone_number=phone_number,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=Role.CUSTOMER,
        )
        return user

    @staticmethod
    def register_wholesale_customer(validated_data: dict) -> tuple[User, WholesaleProfile]:
        """
        Atomically register a wholesale user with WHOLESALE_PENDING role
        and create their initial WholesaleProfile.
        """
        user_data = validated_data["user"]
        company_name = validated_data["company_name"].strip()
        gstin = validated_data["gstin"].strip().upper()
        pan_number = validated_data["pan_number"].strip().upper()
        fssai_license = validated_data.get("fssai_license", "").strip()
        business_type = validated_data.get("business_type", "RETAILER")

        email = user_data["email"].strip().lower()
        phone_number = normalize_indian_phone(user_data["phone_number"])
        password = user_data["password"]
        first_name = user_data.get("first_name", "").strip()
        last_name = user_data.get("last_name", "").strip()

        with transaction.atomic():
            user = User.objects.create_user(
                email=email,
                phone_number=phone_number,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=Role.WHOLESALE_PENDING,
            )

            profile = WholesaleProfile.objects.create(
                user=user,
                company_name=company_name,
                gstin=gstin,
                pan_number=pan_number,
                fssai_license=fssai_license,
                business_type=business_type,
                verification_status=VerificationStatus.PENDING,
            )

        return user, profile

    @staticmethod
    def verify_wholesale_account(
        profile: WholesaleProfile,
        action: str,
        verified_by: User,
        rejection_reason: str = "",
    ) -> WholesaleProfile:
        """
        Approve or reject a wholesale account with strict validation
        and role synchronization.
        """
        action = action.upper().strip()

        with transaction.atomic():
            # Refresh from DB with lock
            profile = WholesaleProfile.objects.select_for_update().get(pk=profile.pk)
            user = profile.user

            if action == "APPROVE":
                profile.verification_status = VerificationStatus.APPROVED
                profile.verified_by = verified_by
                profile.verified_at = timezone.now()
                profile.rejection_reason = ""
                profile.save()

                user.role = Role.WHOLESALE_APPROVED
                user.save(update_fields=["role"])

                logger.info(
                    "Wholesale profile for %s APPROVED by %s",
                    profile.company_name,
                    verified_by.email,
                )

            elif action == "REJECT":
                if not rejection_reason.strip():
                    raise ValidationError(
                        "Rejection reason is required when rejecting a wholesale account."
                    )

                profile.verification_status = VerificationStatus.REJECTED
                profile.verified_by = verified_by
                profile.verified_at = timezone.now()
                profile.rejection_reason = rejection_reason.strip()
                profile.save()

                user.role = Role.WHOLESALE_PENDING
                user.save(update_fields=["role"])

                logger.info(
                    "Wholesale profile for %s REJECTED by %s. Reason: %s",
                    profile.company_name,
                    verified_by.email,
                    rejection_reason,
                )
            else:
                raise ValidationError(
                    f"Invalid verification action '{action}'. Use APPROVE or REJECT."
                )

            return profile

    @staticmethod
    def request_password_reset(email: str) -> None:
        """
        Initiates a password reset request.
        Generates a one-time cryptographically secure token and sends an email.
        Provides strict email enumeration protection: returns successfully regardless
        of whether the email exists in the database.
        """
        clean_email = email.strip().lower()
        user = User.objects.filter(email=clean_email, is_active=True).first()

        if user:
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            base_url = getattr(settings, "FRONTEND_BASE_URL", "http://localhost:3000").rstrip("/")
            reset_url = f"{base_url}/reset-password?uid={uidb64}&token={token}"

            EmailService.send_password_reset_email(user.email, reset_url)
            logger.info("Password reset initiated for user %s", user.email)
        else:
            logger.info("Password reset requested for non-existent or inactive email: %s", clean_email)

    @staticmethod
    def confirm_password_reset(uidb64: str, token: str, new_password: str) -> User:
        """
        Validates the one-time reset token and updates user password.
        The token is cryptographically invalidated immediately upon password change.
        """
        try:
            user_id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.filter(pk=user_id, is_active=True).first()
        except Exception:
            user = None

        if not user or not default_token_generator.check_token(user, token):
            raise ValidationError("This password reset link is invalid or has expired.")

        user.set_password(new_password)
        user.save(update_fields=["password"])

        logger.info("Password successfully reset for user %s", user.email)
        return user

    @staticmethod
    def change_password(user: User, current_password: str, new_password: str) -> None:
        """
        Changes password for an authenticated user after verifying the current password.
        Rejects if current password is incorrect or if new password equals current password.
        """
        if not user.check_password(current_password):
            raise ValidationError({"current_password": "The current password you entered is incorrect."})

        if current_password == new_password:
            raise ValidationError({"new_password": "Your new password cannot be identical to your current password."})

        user.set_password(new_password)
        user.save(update_fields=["password"])

        logger.info("Password successfully changed for user %s", user.email)
