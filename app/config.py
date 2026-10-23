"""Application settings loaded from the environment and server/.env."""

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def _csv(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "")
    admin_email: str = os.getenv("ADMIN_EMAIL", "")
    jwt_secret: str = os.getenv("JWT_SECRET", "")
    token_expiry_hours: int = int(os.getenv("TOKEN_EXPIRY_HOURS", "12"))
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    environment: str = os.getenv("ENVIRONMENT", "production").lower()
    allowed_origins: list[str] = None  # type: ignore[assignment]
    email_api_key: str = os.getenv("EMAIL_API_KEY", "")
    email_sender: str = os.getenv("EMAIL_SENDER", "")
    email_provider: str = os.getenv("EMAIL_PROVIDER", "resend").lower()
    cloudinary_cloud_name: str = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    cloudinary_api_key: str = os.getenv("CLOUDINARY_API_KEY", "")
    cloudinary_api_secret: str = os.getenv("CLOUDINARY_API_SECRET", "")
    max_image_count: int = int(os.getenv("MAX_IMAGES_PER_PROPERTY", "10"))
    max_image_bytes: int = int(os.getenv("MAX_IMAGE_SIZE_MB", "5")) * 1024 * 1024
    public_sold_properties: bool = os.getenv("PUBLIC_SOLD_PROPERTIES", "true").lower() == "true"

    def __post_init__(self) -> None:
        local_origins = "http://localhost:8000,http://127.0.0.1:8000,http://localhost:8001,http://127.0.0.1:8001" if self.debug else ""
        object.__setattr__(self, "allowed_origins", _csv("ALLOWED_ORIGINS", local_origins))

    def validate(self) -> None:
        missing = [key for key, value in (("DATABASE_URL", self.database_url), ("ADMIN_EMAIL", self.admin_email), ("JWT_SECRET", self.jwt_secret)) if not value]
        if missing:
            raise RuntimeError("Missing required environment settings: " + ", ".join(missing))
        if len(self.jwt_secret) < 32:
            raise RuntimeError("JWT_SECRET must contain at least 32 characters")
        if self.debug and self.environment not in {"local", "development"}:
            raise RuntimeError("DEBUG=true is allowed only in a local or development environment")
        if self.environment == "production":
            missing_live = [key for key, value in (("ALLOWED_ORIGINS", self.allowed_origins), ("EMAIL_API_KEY", self.email_api_key), ("EMAIL_SENDER", self.email_sender), ("CLOUDINARY_CLOUD_NAME", self.cloudinary_cloud_name), ("CLOUDINARY_API_KEY", self.cloudinary_api_key), ("CLOUDINARY_API_SECRET", self.cloudinary_api_secret)) if not value]
            if missing_live:
                raise RuntimeError("Missing live environment settings: " + ", ".join(missing_live))


settings = Settings()
