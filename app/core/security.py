from datetime import datetime, timedelta, timezone
import jwt
from app.config import settings

def create_access_token(subject: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(hours=settings.token_expiry_hours)
    return jwt.encode({"sub": subject, "exp": expires}, settings.jwt_secret, algorithm="HS256")

def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
