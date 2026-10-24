import hmac
from app.config import settings

def verify_admin_credentials(email: str, password: str) -> bool:
    """Compare submitted credentials with the single configured admin account."""
    email_matches = hmac.compare_digest(
        email.strip().lower().encode("utf-8"), settings.admin_email.strip().lower().encode("utf-8")
    )
    password_matches = hmac.compare_digest(password.encode("utf-8"), settings.admin_password.encode("utf-8"))
    return bool(settings.admin_email and settings.admin_password and email_matches and password_matches)
