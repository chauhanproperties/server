from sqlalchemy import CheckConstraint, DateTime, Identity, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint("phone", name="uq_customers_phone"),
        CheckConstraint("age IS NULL OR age BETWEEN 0 AND 120", name="ck_customers_age"),
        CheckConstraint("gender IS NULL OR gender IN ('male','female','other')", name="ck_customers_gender"),
    )
    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[str] = mapped_column(Text, nullable=False)
    whatsapp_number: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str | None] = mapped_column(Text)
    age: Mapped[int | None] = mapped_column(Integer)
    gender: Mapped[str | None] = mapped_column(Text)
    registered_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    queries = relationship("Query", back_populates="customer")
    purchases = relationship("Property", back_populates="buyer", foreign_keys="Property.buyer_id")
