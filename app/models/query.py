from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Identity, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Query(Base):
    __tablename__ = "queries"
    __table_args__ = (CheckConstraint("status IN ('new','resolved')", name="ck_queries_status"),)
    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    property_id: Mapped[int | None] = mapped_column(ForeignKey("properties.id", ondelete="SET NULL"), index=True)
    message: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="new", index=True)
    raised_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    resolved_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    customer = relationship("Customer", back_populates="queries")
    property = relationship("Property", back_populates="queries")
