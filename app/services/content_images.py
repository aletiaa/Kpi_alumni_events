from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4
import warnings

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

UPLOAD_ROOT = Path("app/static/uploads")
MAX_IMAGE_BYTES = 5 * 1024 * 1024
IMAGE_FORMATS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp", "GIF": ".gif"}


def validate_image_url(value: str | None) -> str | None:
    value = (value or "").strip()
    if not value:
        return None
    if any(ord(char) < 32 for char in value) or "\\" in value:
        raise ValueError("Некоректне посилання на зображення / Invalid image URL.")
    try:
        parsed = urlsplit(value)
        if value.startswith("/static/") and ".." not in parsed.path.split("/"):
            return value
        if parsed.scheme in {"http", "https"} and parsed.hostname and not parsed.username and not parsed.password:
            return value
    except ValueError:
        pass
    raise ValueError("Вкажіть http:// або https:// посилання на зображення / Enter an HTTP or HTTPS image URL.")


def save_content_image(image_file: UploadFile | None, category: str) -> str | None:
    if not image_file or not image_file.filename:
        return None
    if category not in {"news", "events"}:
        raise ValueError("Invalid upload category")
    payload = image_file.file.read(MAX_IMAGE_BYTES + 1)
    if len(payload) > MAX_IMAGE_BYTES:
        raise ValueError("Зображення має бути до 5 МБ / Image must be at most 5 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(payload)) as image:
                suffix = IMAGE_FORMATS.get(image.format)
                if not suffix:
                    raise ValueError("Unsupported image format")
                image.verify()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValueError("Оберіть справжнє зображення JPG, PNG, WEBP або GIF / Choose a valid JPG, PNG, WEBP or GIF image.") from exc
    directory = UPLOAD_ROOT / category
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{suffix}"
    (directory / filename).write_bytes(payload)
    return f"/static/uploads/{category}/{filename}"


def resolve_content_image(image_file: UploadFile | None, image_url: str, category: str) -> str | None:
    # A selected file replaces the URL; remote images are not fetched by the server.
    if image_file and image_file.filename:
        return save_content_image(image_file, category)
    return validate_image_url(image_url)
