from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import PyJWTError
from app.config import settings
from app.core.security import decode_access_token

bearer = HTTPBearer(auto_error=False)

def require_admin(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> str:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Please log in again.")
    try:
        payload = decode_access_token(credentials.credentials)
        if payload.get("sub", "").lower() != settings.admin_email.lower():
            raise ValueError("Invalid token subject")
        return payload["sub"]
    except (PyJWTError, ValueError, KeyError):
        raise HTTPException(status_code=401, detail="Your session expired. Please log in again.") from None
