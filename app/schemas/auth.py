from pydantic import BaseModel, EmailStr, Field, field_validator

class AdminLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)

    @field_validator("password", mode="before")
    @classmethod
    def validate_password(cls, value):
        if isinstance(value, str) and not value.strip():
            raise ValueError("Password is required")
        return value
