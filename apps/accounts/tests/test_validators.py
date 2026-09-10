from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.validators import (
    mask_gstin,
    mask_pan,
    mask_phone,
    normalize_indian_phone,
    validate_gstin,
    validate_pan,
    validate_pincode,
)


class ValidatorTests(TestCase):
    """Automated unit tests for Indian phone, GSTIN, PAN, and Pincode validators."""

    def test_phone_normalization_valid_formats(self):
        valid_cases = [
            ("+919876543210", "+919876543210"),
            ("919876543210", "+919876543210"),
            ("09876543210", "+919876543210"),
            ("9876543210", "+919876543210"),
            ("+91 98765-43210", "+919876543210"),
            ("91-9876543210", "+919876543210"),
            ("  (98765) 43210 ", "+919876543210"),
            ("6123456789", "+916123456789"),
            ("7123456789", "+917123456789"),
            ("8123456789", "+918123456789"),
        ]
        for raw, expected in valid_cases:
            self.assertEqual(normalize_indian_phone(raw), expected)

    def test_phone_validation_rejects_invalid(self):
        invalid_cases = [
            "5123456789",  # Starts with 5 (invalid Indian mobile)
            "12345",  # Too short
            "98765432100",  # Too long
            "abcdefghij",  # Letters
            "",  # Empty
            None,  # None
            "+14155552671",  # US number
        ]
        for invalid in invalid_cases:
            with self.assertRaises(ValidationError):
                normalize_indian_phone(invalid)

    def test_gstin_validation(self):
        valid_gstin = "29ABCDE1234F1Z5"
        self.assertIsNone(validate_gstin(valid_gstin))

        invalid_gstins = [
            "29ABCDE1234F1Z",  # 14 chars
            "29ABCDE1234F1Z55",  # 16 chars
            "29123451234F1Z5",  # Digits instead of PAN letters
            "INVALID_GSTIN!!",
        ]
        for invalid in invalid_gstins:
            with self.assertRaises(ValidationError):
                validate_gstin(invalid)

    def test_pan_validation(self):
        valid_pan = "ABCDE1234F"
        self.assertIsNone(validate_pan(valid_pan))

        invalid_pans = [
            "ABCD1234F",  # 9 chars
            "ABCDE12345F",  # 11 chars
            "12345ABCDE",  # Inverted pattern
            "abcde1234f!",  # Special chars
        ]
        for invalid in invalid_pans:
            with self.assertRaises(ValidationError):
                validate_pan(invalid)

    def test_pincode_validation(self):
        valid_pincodes = ["577401", "560001", "110001", "400001"]
        for p in valid_pincodes:
            self.assertIsNone(validate_pincode(p))

        invalid_pincodes = [
            "012345",  # Cannot start with 0
            "57740",  # 5 digits
            "5774011",  # 7 digits
            "57740A",  # Contains letter
            "",  # Empty
        ]
        for invalid in invalid_pincodes:
            with self.assertRaises(ValidationError):
                validate_pincode(invalid)

    def test_masking_functions(self):
        self.assertEqual(mask_gstin("29ABCDE1234F1Z5"), "29ABCDE****F1Z5")
        self.assertEqual(mask_pan("ABCDE1234F"), "ABCDE****F")
        self.assertEqual(mask_phone("+919876543210"), "+91******3210")
