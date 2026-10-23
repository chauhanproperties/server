from datetime import datetime
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from app.core.dependencies import require_admin
from app.database import get_db
from app.models.property import Property
from app.schemas.property import PropertyInput, SoldInput, _validate_optional_email, _validate_optional_phone, _trim_text
from app.services.property_service import delete_property, get_property, list_properties, property_dict, save_property, set_available, set_sold

router = APIRouter(prefix="/api/admin/properties", tags=["admin properties"], dependencies=[Depends(require_admin)])

class PropertyStatus(BaseModel):
    status: Literal["available", "sold"]
    buyer_name: str | None = Field(default=None, min_length=1, max_length=200)
    buyer_phone: str | None = None
    buyer_whatsapp_number: str | None = None
    buyer_email: str | None = None
    sold_at: datetime | None = None
    sale_price: float | None = Field(default=None, ge=0)

    @field_validator("buyer_name", mode="before")
    @classmethod
    def trim_buyer_name(cls, value):
        return _trim_text(value)

    @field_validator("buyer_phone", mode="before")
    @classmethod
    def validate_buyer_phone(cls, value):
        return _validate_optional_phone(value, "buyer phone number")

    @field_validator("buyer_whatsapp_number", mode="before")
    @classmethod
    def validate_buyer_whatsapp(cls, value):
        return _validate_optional_phone(value, "buyer WhatsApp number")

    @field_validator("buyer_email", mode="before")
    @classmethod
    def validate_buyer_email(cls, value):
        return _validate_optional_email(value)

@router.get("")
def properties(property_type: str | None = None, status: str | None = None, min_price: float | None = None, max_price: float | None = None, search: str | None = None, sort: str = "newest", page: int = QueryParam(1, ge=1), page_size: int = QueryParam(20, ge=1, le=100), db: Session = Depends(get_db)):
    if property_type and property_type not in {"plot", "house", "flat"}:
        raise HTTPException(422, "Invalid property type")
    if status and status not in {"available", "sold"}:
        raise HTTPException(422, "Invalid status")
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(422, "Minimum price must not exceed maximum price")
    return list_properties(db, property_type=property_type, status=status, min_price=min_price, max_price=max_price, search=search, sort=sort, page=page, page_size=page_size)

@router.get("/{property_id}")
def get_one(property_id: int, db: Session = Depends(get_db)):
    item = get_property(db, property_id)
    if not item:
        raise HTTPException(404, "Property not found")
    return property_dict(item)

@router.post("")
def create(data: PropertyInput, db: Session = Depends(get_db)):
    try:
        return property_dict(save_property(db, data))
    except Exception:
        db.rollback()
        raise

@router.put("/{property_id}")
def update(property_id: int, data: PropertyInput, db: Session = Depends(get_db)):
    item = db.get(Property, property_id)
    if not item:
        raise HTTPException(404, "Property not found")
    try:
        return property_dict(save_property(db, data, item))
    except Exception:
        db.rollback()
        raise

@router.delete("/{property_id}", status_code=204)
def delete(property_id: int, db: Session = Depends(get_db)):
    item = get_property(db, property_id)
    if not item:
        raise HTTPException(404, "Property not found")
    try:
        delete_property(db, item)
    except Exception:
        db.rollback()
        raise HTTPException(502, "The property could not be deleted from the database. Try again.") from None

@router.patch("/{property_id}/status")
def change_status(property_id: int, data: PropertyStatus, db: Session = Depends(get_db)):
    item = db.get(Property, property_id)
    if not item:
        raise HTTPException(404, "Property not found")
    try:
        if data.status == "available":
            item = set_available(db, item)
        else:
            if not data.buyer_name or not data.buyer_phone or not data.buyer_whatsapp_number:
                raise HTTPException(422, "Buyer name, phone and WhatsApp number are required to mark a property sold.")
            sold = SoldInput(buyer_name=data.buyer_name, buyer_phone=data.buyer_phone, buyer_whatsapp_number=data.buyer_whatsapp_number, buyer_email=data.buyer_email, sold_at=data.sold_at, sale_price=data.sale_price)
            item = set_sold(db, item, sold)
        return property_dict(item)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from None
