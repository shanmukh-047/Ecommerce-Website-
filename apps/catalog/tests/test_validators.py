from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from apps.catalog.validators import MAX_IMAGE_SIZE_BYTES, validate_image_file


class ImageValidatorTests(TestCase):
    """
    Tests image upload verification:
    - Pillow format check (JPEG, PNG, WEBP)
    - File size constraints (<= 5MB)
    - Rejection of corrupted files, malicious scripts, or forged extensions
    """

    def test_valid_jpeg_passes(self):
        buf = BytesIO()
        img = Image.new("RGB", (50, 50), color="red")
        img.save(buf, format="JPEG")
        buf.seek(0)
        uploaded = SimpleUploadedFile("sample.jpg", buf.read(), content_type="image/jpeg")
        # Should not raise
        validate_image_file(uploaded)

    def test_valid_png_passes(self):
        buf = BytesIO()
        img = Image.new("RGB", (50, 50), color="blue")
        img.save(buf, format="PNG")
        buf.seek(0)
        uploaded = SimpleUploadedFile("sample.png", buf.read(), content_type="image/png")
        validate_image_file(uploaded)

    def test_valid_webp_passes(self):
        buf = BytesIO()
        img = Image.new("RGB", (50, 50), color="yellow")
        img.save(buf, format="WEBP")
        buf.seek(0)
        uploaded = SimpleUploadedFile("sample.webp", buf.read(), content_type="image/webp")
        validate_image_file(uploaded)

    def test_unsupported_extension_rejected(self):
        buf = BytesIO()
        img = Image.new("RGB", (50, 50), color="green")
        img.save(buf, format="GIF")
        buf.seek(0)
        uploaded = SimpleUploadedFile("sample.gif", buf.read(), content_type="image/gif")
        with self.assertRaises(ValidationError) as ctx:
            validate_image_file(uploaded)
        self.assertIn("Unsupported image file extension", str(ctx.exception))

    def test_oversized_image_rejected(self):
        # Create a mock file with size reporting over 5MB
        fake_content = b"x" * 100
        uploaded = SimpleUploadedFile("oversized.jpg", fake_content, content_type="image/jpeg")
        uploaded.size = MAX_IMAGE_SIZE_BYTES + 1024
        with self.assertRaises(ValidationError) as ctx:
            validate_image_file(uploaded)
        self.assertIn("Image file size exceeds the 5MB maximum limit", str(ctx.exception))

    def test_corrupted_file_or_mime_spoofing_rejected(self):
        # Text file masquerading as .jpg
        fake_content = b"<?php echo 'malicious payload'; ?>"
        uploaded = SimpleUploadedFile("exploit.jpg", fake_content, content_type="image/jpeg")
        with self.assertRaises(ValidationError) as ctx:
            validate_image_file(uploaded)
        self.assertIn("not a valid or readable image", str(ctx.exception))
