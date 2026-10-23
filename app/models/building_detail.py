from sqlalchemy import CheckConstraint, Computed, ForeignKey, Identity, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class BuildingDetail(Base):
    __tablename__ = "building_details"
    __table_args__ = (
        CheckConstraint("bedrooms >= 0", name="ck_building_bedrooms"),
        CheckConstraint("kitchens >= 0", name="ck_building_kitchens"),
        CheckConstraint("bathrooms >= 0", name="ck_building_bathrooms"),
        CheckConstraint("building_area >= 0", name="ck_building_area"),
        CheckConstraint("garden_area IS NULL OR garden_area >= 0", name="ck_building_garden_area"),
        CheckConstraint("parking_area IS NULL OR parking_area >= 0", name="ck_building_parking_area"),
        UniqueConstraint("property_id", name="uq_building_property"),
    )
    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)
    bedrooms: Mapped[int] = mapped_column(Integer, nullable=False)
    kitchens: Mapped[int] = mapped_column(Integer, nullable=False)
    bathrooms: Mapped[int] = mapped_column(Integer, nullable=False)
    garden_area: Mapped[float | None] = mapped_column(Numeric(10, 2), server_default="0")
    parking_area: Mapped[float | None] = mapped_column(Numeric(10, 2), server_default="0")
    building_area: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    total_area: Mapped[float] = mapped_column(Numeric(12, 2), Computed("building_area + COALESCE(garden_area, 0) + COALESCE(parking_area, 0)", persisted=True))
    property = relationship("Property", back_populates="building_details")
