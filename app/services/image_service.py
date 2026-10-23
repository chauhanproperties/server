import cloudinary
import cloudinary.uploader
import uuid
from app.config import settings

ALLOWED_FORMATS = {"image/jpeg", "image/png", "image/webp"}

def _configure() -> None:
    cloudinary.config(cloud_name=settings.cloudinary_cloud_name, api_key=settings.cloudinary_api_key, api_secret=settings.cloudinary_api_secret, secure=True)

def upload_image(data: bytes, content_type: str | None) -> dict:
    if content_type not in ALLOWED_FORMATS:
        raise ValueError("Use a JPG, PNG, or WebP image.")
    if not data or len(data) > settings.max_image_bytes:
        raise ValueError("Each image must be smaller than the configured size limit.")
    if not settings.cloudinary_cloud_name or not settings.cloudinary_api_key or not settings.cloudinary_api_secret:
        raise RuntimeError("Cloudinary is not configured. Add its credentials to server/.env.")
    _configure()
    return cloudinary.uploader.upload(data, folder="chauhan-properties", resource_type="image", public_id=uuid.uuid4().hex, allowed_formats=["jpg", "png", "webp"])

def delete_image(public_id: str | None) -> None:
    if not public_id:
        return
    _configure()
    cloudinary.uploader.destroy(public_id, resource_type="image", invalidate=True)
