from pydantic import BaseModel, ConfigDict, EmailStr, Field

class CustomerInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    phone: str = Field(min_length=7, max_length=24)
    whatsapp_number: str = Field(min_length=7, max_length=24)
    email: EmailStr | None = None

class CustomerUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr | None = None
    age: int | None = Field(default=None, ge=0, le=120)
    gender: str | None = None
