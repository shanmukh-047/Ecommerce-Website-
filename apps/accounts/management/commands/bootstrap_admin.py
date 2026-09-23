import os
import sys

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import transaction

from apps.accounts.models import Role, User
from apps.accounts.validators import normalize_indian_phone


class Command(BaseCommand):
    help = (
        "Safe, one-time production administrative superuser bootstrap command. "
        "Strictly gated by BOOTSTRAP_ADMIN=true environment variable."
    )

    def handle(self, *args, **options):
        # 1. Gate check: Must be explicitly enabled
        bootstrap_flag = os.environ.get("BOOTSTRAP_ADMIN", "").strip().lower()
        if bootstrap_flag != "true":
            raise CommandError(
                "Execution refused: BOOTSTRAP_ADMIN environment variable must be explicitly set to 'true'. "
                "This is a one-time administrative provisioning mechanism and remains locked by default."
            )

        # 2. Extract and validate ADMIN_EMAIL
        raw_email = os.environ.get("ADMIN_EMAIL", "").strip()
        if not raw_email:
            raise CommandError(
                "Execution refused: ADMIN_EMAIL environment variable is required but missing or empty."
            )

        admin_email = raw_email.lower()
        try:
            validate_email(admin_email)
        except ValidationError as exc:
            raise CommandError(
                f"Execution refused: ADMIN_EMAIL '{admin_email}' is not a valid email address."
            ) from exc

        # 3. Extract and validate ADMIN_PASSWORD (never print or log this value!)
        admin_password = os.environ.get("ADMIN_PASSWORD", "").strip()
        if not admin_password:
            raise CommandError(
                "Execution refused: ADMIN_PASSWORD environment variable is required but missing or empty."
            )

        try:
            validate_password(admin_password)
        except ValidationError as exc:
            raise CommandError(
                f"Execution refused: ADMIN_PASSWORD does not meet security requirements: "
                f"{'; '.join(exc.messages)}"
            ) from exc

        # 4. Resolve phone number (User model requires normalized Indian phone number)
        raw_phone = os.environ.get("ADMIN_PHONE", "").strip()
        if not raw_phone:
            # Canonical administrative default emergency contact
            raw_phone = "+919876543210"

        try:
            admin_phone = normalize_indian_phone(raw_phone)
        except ValidationError as exc:
            raise CommandError(
                f"Execution refused: ADMIN_PHONE '{raw_phone}' is invalid: {'; '.join(exc.messages)}"
            ) from exc

        first_name = os.environ.get("ADMIN_FIRST_NAME", "Super").strip() or "Super"
        last_name = os.environ.get("ADMIN_LAST_NAME", "Administrator").strip() or "Administrator"

        # 5. Atomic user creation or update
        with transaction.atomic():
            user = User.objects.filter(email=admin_email).first()

            if user:
                # Update existing user to superadmin
                user.role = Role.SUPERADMIN
                user.is_staff = True
                user.is_superuser = True
                user.is_active = True
                user.first_name = user.first_name or first_name
                user.last_name = user.last_name or last_name
                user.set_password(admin_password)
                user.save()
                action_desc = "Updated existing user to Super Administrator and reset password"
            else:
                # Ensure phone number isn't occupied by a different account
                existing_phone_user = User.objects.filter(phone_number=admin_phone).first()
                if existing_phone_user:
                    # Try emergency secondary administrative phone number
                    fallback_phone = normalize_indian_phone("9999999999")
                    if User.objects.filter(phone_number=fallback_phone).exists():
                        raise CommandError(
                            f"Phone number {admin_phone} is already linked to account "
                            f"'{existing_phone_user.email}'. Please set a distinct ADMIN_PHONE in environment."
                        )
                    admin_phone = fallback_phone

                user = User(
                    email=admin_email,
                    phone_number=admin_phone,
                    first_name=first_name,
                    last_name=last_name,
                    role=Role.SUPERADMIN,
                    is_staff=True,
                    is_superuser=True,
                    is_active=True,
                )
                user.set_password(admin_password)
                user.save()
                action_desc = "Created new Super Administrator account"

        # 6. Inform operator (ZERO password exposure)
        self.stdout.write(self.style.SUCCESS("=" * 64))
        self.stdout.write(self.style.SUCCESS("==> BHARATH MASALA: ADMIN BOOTSTRAP COMPLETE"))
        self.stdout.write(self.style.SUCCESS(f"==> Status:      {action_desc}"))
        self.stdout.write(self.style.SUCCESS(f"==> Account:     {user.email}"))
        self.stdout.write(self.style.SUCCESS(f"==> Role:        {user.get_role_display()}"))
        self.stdout.write(
            self.style.SUCCESS(
                f"==> Flags:       is_staff={user.is_staff}, is_superuser={user.is_superuser}, is_active={user.is_active}"
            )
        )
        self.stdout.write(self.style.WARNING("=" * 64))
        self.stdout.write(self.style.WARNING("CRITICAL ACTION REQUIRED ON RENDER DASHBOARD:"))
        self.stdout.write(
            self.style.WARNING("1. Set BOOTSTRAP_ADMIN=false (or delete the variable).")
        )
        self.stdout.write(
            self.style.WARNING("2. DELETE the ADMIN_PASSWORD environment variable immediately.")
        )
        self.stdout.write(self.style.WARNING("=" * 64))
