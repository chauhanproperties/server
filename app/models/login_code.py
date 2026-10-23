from sqlalchemy import Boolean, DateTime, Identity, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class LoginCode(Base):
    __tablename__ = "login_codes"
    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    code_hash: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
