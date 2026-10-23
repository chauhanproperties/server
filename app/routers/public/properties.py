from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.property import Property
from app.services.property_service import get_property, list_properties, property_dict

router = APIRouter(prefix="/api/public/properties", tags=["public properties"])

@router.get("")
def properties(property_type: str | None = None, status: str | None = None, min_price: float | None = None, max_price: float | None = None, sort: str = "newest", page: int = QueryParam(1, ge=1), page_size: int = QueryParam(20, ge=1, le=100), db: Session = Depends(get_db)):
    return list_properties(db, public=True, property_type=property_type, status=status, min_price=min_price, max_price=max_price, sort=sort, page=page, page_size=page_size)

@router.get("/{property_id}")
def get_one(property_id: int, db: Session = Depends(get_db)):
    item = get_property(db, property_id)
    if not item:
        raise HTTPException(404, "Property not found")
    if item.status == "sold" and not __import__("app.config", fromlist=["settings"]).settings.public_sold_properties:
        raise HTTPException(404, "Property not found")
    return property_dict(item, public=True)
