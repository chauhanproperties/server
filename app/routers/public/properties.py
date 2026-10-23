from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.services.property_service import get_property, list_properties, property_dict

router = APIRouter(prefix="/api/public/properties", tags=["public properties"])

@router.get("")
def properties(property_type: str | None = None, status: str | None = None, min_price: float | None = None, max_price: float | None = None, sort: str = "newest", page: int = QueryParam(1, ge=1), page_size: int = QueryParam(20, ge=1, le=100), db: Session = Depends(get_db)):
    if property_type and property_type not in {"plot", "house", "flat"}:
        raise HTTPException(422, "Invalid property type")
    if status and status not in {"available", "sold"}:
        raise HTTPException(422, "Invalid status")
    if sort not in {"newest", "oldest", "price_asc", "price_desc"}:
        raise HTTPException(422, "Invalid sort order")
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(422, "Minimum price must not exceed maximum price")
    return list_properties(db, public=True, property_type=property_type, status=status, min_price=min_price, max_price=max_price, sort=sort, page=page, page_size=page_size)

@router.get("/{property_id}")
def get_one(property_id: int, db: Session = Depends(get_db)):
    item = get_property(db, property_id)
    if not item:
        raise HTTPException(404, "Property not found")
    if item.status == "sold" and not settings.public_sold_properties:
        raise HTTPException(404, "Property not found")
    return property_dict(item, public=True)
