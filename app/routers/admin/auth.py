from fastapi import APIRouter, Depends, HTTPException, Request
from app.config import settings
from app.core.dependencies import require_admin
from app.core.rate_limit import client_ip, enforce_rate_limit
from app.core.security import create_access_token
from app.schemas.auth import AdminLogin
from app.services.auth_service import verify_admin_credentials

router = APIRouter(prefix="/api/admin/auth", tags=["admin authentication"])

@router.post("/login")
def login(data: AdminLogin, request: Request):
    enforce_rate_limit(client_ip(request), scope="admin-login-ip", limit=10, window_seconds=900,
                       message="Too many login attempts. Please wait 15 minutes and try again.")
    if not verify_admin_credentials(str(data.email), data.password):
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    return {"access_token": create_access_token(settings.admin_email), "token_type": "bearer"}

@router.get("/me")
def me(admin_email: str = Depends(require_admin)):
    return {"email": admin_email}
