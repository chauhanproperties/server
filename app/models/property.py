from sqlalchemy import CheckConstraint, Computed, DateTime, ForeignKey, Identity, Integer, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Property(Base):
    __tablename__ = "properties"
    __table_args__ = (
        CheckConstraint("property_type IN ('plot','house','flat')", name="ck_properties_type"),
        CheckConstraint("length > 0", name="ck_properties_length_positive"),
        CheckConstraint("width > 0", name="ck_properties_width_positive"),
        CheckConstraint("price >= 0", name="ck_properties_price_nonnegative"),
        CheckConstraint("status IN ('available','sold')", name="ck_properties_status"),
        CheckConstraint("latitude IS NULL OR latitude BETWEEN -90 AND 90", name="ck_properties_latitude"),
        CheckConstraint("longitude IS NULL OR longitude BETWEEN -180 AND 180", name="ck_properties_longitude"),
        CheckConstraint("sale_price IS NULL OR sale_price >= 0", name="ck_properties_sale_price"),
    )
    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    property_type: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    length: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    width: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    area: Mapped[float] = mapped_column(Numeric(14, 2), Computed("length * width", persisted=True))
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, index=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="available", index=True)
    latitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    maps_url: Mapped[str | None] = mapped_column(Text)
    buyer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"))
    sold_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    sale_price: Mapped[float | None] = mapped_column(Numeric(14, 2))
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    building_details = relationship("BuildingDetail", back_populates="property", cascade="all, delete-orphan", uselist=False)
    images = relationship("PropertyImage", back_populates="property", cascade="all, delete-orphan", order_by="PropertyImage.display_order")
    buyer = relationship("Customer", back_populates="purchases", foreign_keys=[buyer_id])
    queries = relationship("Query", back_populates="property")
