from sqlalchemy import ForeignKey, Identity, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class PropertyImage(Base):
    __tablename__ = "property_images"
    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    public_id: Mapped[str | None] = mapped_column(Text)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    property = relationship("Property", back_populates="images")
