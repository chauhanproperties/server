from pydantic import BaseModel, EmailStr, Field

class RequestCode(BaseModel):
    email: EmailStr

class VerifyCode(BaseModel):
    email: EmailStr
    code: str = Field(pattern=r"^\d{8}$")

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
