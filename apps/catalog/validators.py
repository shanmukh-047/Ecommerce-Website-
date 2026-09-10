import os
import uuid

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_PIL_FORMATS = {"JPEG", "PNG", "WEBP"}


def validate_image_file(image_file):
    """
    Validate uploaded image files for:
    1. Maximum file size (5MB).
    2. File extension validity (.jpg, .jpeg, .png, .webp).
    3. True image file header and format integrity via Pillow (prevent MIME spoofing).
    """
    if not image_file:
        return

    # 1. Size verification
    if hasattr(image_file, "size") and image_file.size > MAX_IMAGE_SIZE_BYTES:
        raise ValidationError(
            f"Image file size exceeds the 5MB maximum limit. Current size: {image_file.size / (1024 * 1024):.2f}MB."
        )

    # 2. File extension verification
    file_name = getattr(image_file, "name", "")
    _, ext = os.path.splitext(file_name.lower())
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(
            f"Unsupported image file extension '{ext}'. Allowed extensions are: {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}."
        )

    # 3. Pillow header and format inspection
    try:
        # If file is in memory or on disk, preserve cursor position
        pos = image_file.tell() if hasattr(image_file, "tell") else 0
        img = Image.open(image_file)
        img.verify()

        # Check detected format
        if img.format not in ALLOWED_PIL_FORMATS:
            raise ValidationError(
                f"Invalid image format '{img.format}'. Allowed formats are: {', '.join(sorted(ALLOWED_PIL_FORMATS))}."
            )

        # Reset pointer after inspection
        if hasattr(image_file, "seek"):
            image_file.seek(pos)
    except (UnidentifiedImageError, OSError, SyntaxError) as e:
        raise ValidationError(f"The uploaded file is not a valid or readable image: {str(e)}")


def category_image_upload_path(instance, filename):
    """Generate safe, collision-proof UUID storage paths for category images."""
    _, ext = os.path.splitext(filename.lower())
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        ext = ".jpg"
    return f"categories/{uuid.uuid4().hex}{ext}"


def product_image_upload_path(instance, filename):
    """Generate safe, collision-proof UUID storage paths for product gallery images."""
    _, ext = os.path.splitext(filename.lower())
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        ext = ".jpg"
    product_id = instance.product_id if instance.product_id else "unassigned"
    return f"products/{product_id}/{uuid.uuid4().hex}{ext}"


def review_image_upload_path(instance, filename):
    """Generate safe, collision-proof UUID storage paths for customer review images."""
    _, ext = os.path.splitext(filename.lower())
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        ext = ".jpg"
    review_id = instance.review_id if instance.review_id else "unassigned"
    return f"reviews/{review_id}/{uuid.uuid4().hex}{ext}"
