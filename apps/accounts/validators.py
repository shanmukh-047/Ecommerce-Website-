import re

from django.core.exceptions import ValidationError

# Indian Mobile Phone Regex: Optional +91 or 91 or 0 prefix followed by 10 digits starting with 6-9
INDIAN_PHONE_REGEX = re.compile(r"^(?:\+91|91|0)?([6-9]\d{9})$")

# Indian GSTIN: 2-digit state code, 10-char PAN, 1 entity digit, Z (default), 1 check digit
GSTIN_REGEX = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")

# Indian Permanent Account Number (PAN): 5 uppercase letters, 4 digits, 1 uppercase letter
PAN_REGEX = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$")

# Indian Postal Pincode: 6 digits, cannot start with 0
PINCODE_REGEX = re.compile(r"^[1-9][0-9]{5}$")


def normalize_indian_phone(value: str) -> str:
    """
    Normalizes any valid Indian phone number into canonical E.164 format: +91XXXXXXXXXX
    Strips spaces, dashes, dots, and common international dialing prefixes.
    """
    if not value:
        raise ValidationError("Phone number is required.")

    cleaned = re.sub(r"[\s\-\.\(\)]", "", str(value).strip())
    match = INDIAN_PHONE_REGEX.match(cleaned)
    if not match:
        raise ValidationError(
            "Enter a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9."
        )

    ten_digits = match.group(1)
    return f"+91{ten_digits}"


def validate_indian_phone(value: str) -> None:
    """Validator suitable for Django model fields."""
    normalize_indian_phone(value)


def validate_gstin(value: str) -> None:
    """Validates 15-character Indian Goods and Services Tax Identification Number."""
    if not value:
        return
    cleaned = value.strip().upper()
    if not GSTIN_REGEX.match(cleaned):
        raise ValidationError(
            "Invalid GSTIN format. Expected 15 characters (e.g., 29ABCDE1234F1Z5)."
        )


def validate_pan(value: str) -> None:
    """Validates 10-character Indian Income Tax PAN."""
    if not value:
        return
    cleaned = value.strip().upper()
    if not PAN_REGEX.match(cleaned):
        raise ValidationError(
            "Invalid PAN format. Expected 10 alphanumeric characters (e.g., ABCDE1234F)."
        )


def validate_pincode(value: str) -> None:
    """Validates 6-digit Indian Postal PIN Code."""
    if not value:
        raise ValidationError("Pincode is required.")
    cleaned = str(value).strip()
    if not PINCODE_REGEX.match(cleaned):
        raise ValidationError(
            "Invalid Indian Pincode. Must be exactly 6 digits without starting with 0."
        )


def mask_gstin(gstin: str) -> str:
    """Masks middle characters of GSTIN for safe read-only display: 29ABCDE****1Z5"""
    if not gstin or len(gstin) != 15:
        return gstin
    return f"{gstin[:7]}****{gstin[11:]}"


def mask_pan(pan: str) -> str:
    """Masks middle digits of PAN for safe read-only display: ABCDE****F"""
    if not pan or len(pan) != 10:
        return pan
    return f"{pan[:5]}****{pan[9:]}"


def mask_phone(phone: str) -> str:
    """Masks phone number: +91******3210"""
    if not phone or len(phone) < 10:
        return phone
    return f"{phone[:3]}******{phone[-4:]}"
