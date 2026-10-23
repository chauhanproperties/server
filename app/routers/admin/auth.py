from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.config import settings
from app.core.dependencies import require_admin
from app.core.rate_limit import client_ip, enforce_rate_limit
from app.core.security import create_access_token
from app.database import get_db
from app.schemas.auth import RequestCode, VerifyCode
from app.services.auth_service import request_code, verify_code

router = APIRouter(prefix="/api/admin/auth", tags=["admin authentication"])

@router.post("/request-code")
def request_login_code(data: RequestCode, request: Request, db: Session = Depends(get_db)):
    enforce_rate_limit(client_ip(request), scope="request-login-code-ip", limit=5, window_seconds=3600,
                       message="Too many login code requests from this network. Please try again later.")
    request_code(db, str(data.email))
    return {"message": "If this email is allowed, a code has been sent."}

@router.post("/verify-code")
def verify_login_code(data: VerifyCode, request: Request, db: Session = Depends(get_db)):
    enforce_rate_limit(client_ip(request), scope="verify-login-code-ip", limit=10, window_seconds=3600,
                       message="Too many code attempts from this network. Please try again later.")
    if data.email.strip().lower() != settings.admin_email.strip().lower() or not verify_code(db, data.code):
        raise HTTPException(status_code=400, detail="That code is invalid or expired. Request a new code and try again.")
    return {"access_token": create_access_token(settings.admin_email), "token_type": "bearer"}

@router.get("/me")
def me(admin_email: str = Depends(require_admin)):
    return {"email": admin_email}
