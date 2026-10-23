from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import logging
import secrets
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session
from app.config import settings
from app.models.login_code import LoginCode
from app.services.email_service import send_login_code

logger = logging.getLogger(__name__)

def _hash(code: str) -> str:
    return hmac.new(settings.jwt_secret.encode(), code.encode(), hashlib.sha256).hexdigest()

def request_code(db: Session, email: str) -> bool:
    now = datetime.now(timezone.utc)
    db.execute(LoginCode.__table__.delete().where(LoginCode.created_at < now - timedelta(days=1)))
    db.commit()
    if email.strip().lower() != settings.admin_email.strip().lower():
        return False
    hour_ago, day_ago = now - timedelta(hours=1), now - timedelta(days=1)
    recent_hour = db.scalar(select(func.count(LoginCode.id)).where(LoginCode.created_at >= hour_ago)) or 0
    recent_day = db.scalar(select(func.count(LoginCode.id)).where(LoginCode.created_at >= day_ago)) or 0
    if recent_hour >= 3 or recent_day >= 10:
        return False
    code = f"{secrets.randbelow(100_000_000):08d}"
    row = LoginCode(code_hash=_hash(code), expires_at=now + timedelta(minutes=10))
    db.add(row)
    db.commit()
    try:
        send_login_code(settings.admin_email, code)
    except Exception:
        logger.exception("Login code email could not be delivered")
        row.used = True
        db.commit()
        return False
    db.execute(update(LoginCode).where(LoginCode.id != row.id, LoginCode.used.is_(False)).values(used=True))
    db.commit()
    return True

def verify_code(db: Session, code: str) -> bool:
    now = datetime.now(timezone.utc)
    row = db.scalar(select(LoginCode).where(LoginCode.used.is_(False), LoginCode.expires_at > now).order_by(LoginCode.created_at.desc()).with_for_update())
    if row is None:
        return False
    if not hmac.compare_digest(row.code_hash, _hash(code)):
        row.attempts += 1
        if row.attempts >= 5:
            row.used = True
        db.commit()
        return False
    row.used = True
    db.commit()
    return True
