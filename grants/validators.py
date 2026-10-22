from io import BytesIO
from pathlib import Path
import warnings

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError


MAX_UPLOAD_SIZE = 10 * 1024 * 1024
ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
PDF_SIGNATURE = b"%PDF-"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def validate_request_upload(uploaded_file):
    if uploaded_file.size > MAX_UPLOAD_SIZE:
        raise ValidationError("Each file must be 10 MiB or smaller.")

    extension = Path(uploaded_file.name).suffix.lower()
    if extension not in ALLOWED_UPLOAD_EXTENSIONS:
        raise ValidationError("Only PDF, JPG, JPEG, or PNG files are allowed.")

    header = uploaded_file.read(8)
    uploaded_file.seek(0)

    if extension == ".pdf":
        if not header.startswith(PDF_SIGNATURE):
            raise ValidationError("The uploaded file is not a valid PDF.")
        return

    if extension == ".png":
        has_valid_signature = header.startswith(PNG_SIGNATURE)
    else:
        has_valid_signature = header.startswith(b"\xff\xd8\xff")

    if not has_valid_signature:
        raise ValidationError("The uploaded file content does not match its file type.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(uploaded_file.read())) as image:
                if image.format not in {"JPEG", "PNG"}:
                    raise ValidationError("Only valid JPEG or PNG images are allowed.")
                image.verify()
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        UnidentifiedImageError,
    ) as error:
        raise ValidationError("The uploaded image is invalid or cannot be processed.") from error
    finally:
        uploaded_file.seek(0)
