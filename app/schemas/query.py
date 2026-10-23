from pydantic import BaseModel, EmailStr, Field

class QueryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    phone: str = Field(min_length=7, max_length=24)
    whatsapp_number: str = Field(min_length=7, max_length=24)
    property_id: int | None = Field(default=None, gt=0)
    email: EmailStr | None = None
    message: str | None = Field(default=None, max_length=5000)

class EmailReply(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=10000)
