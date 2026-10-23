from datetime import datetime, timezone
import logging
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload
from app.config import settings
from app.models.property import Property
from app.models.property_image import PropertyImage
from app.models.building_detail import BuildingDetail
from app.models.customer import Customer
from app.schemas.property import PropertyInput, SoldInput
from app.services.customer_service import find_or_create
from app.services.image_service import delete_image

logger = logging.getLogger(__name__)

def property_dict(item: Property, public: bool = False) -> dict:
    data = {
        "id": item.id, "title": item.title, "property_type": item.property_type,
        "address": item.address, "length": float(item.length), "width": float(item.width),
        "area": float(item.area), "description": item.description, "price": float(item.price),
        "status": item.status, "latitude": float(item.latitude) if item.latitude is not None else None,
        "longitude": float(item.longitude) if item.longitude is not None else None,
        "maps_url": item.maps_url, "created_at": item.created_at, "updated_at": item.updated_at,
        "images": [{"id": image.id, "image_url": image.image_url, **({} if public else {"public_id": image.public_id}), "display_order": image.display_order} for image in item.images],
        "building_details": None,
    }
    if item.building_details:
        b = item.building_details
        data["building_details"] = {"bedrooms": b.bedrooms, "kitchens": b.kitchens, "bathrooms": b.bathrooms, "building_area": float(b.building_area), "garden_area": float(b.garden_area or 0), "parking_area": float(b.parking_area or 0), "total_area": float(b.total_area)}
    if not public:
        data.update({"buyer_id": item.buyer_id, "sold_at": item.sold_at, "sale_price": float(item.sale_price) if item.sale_price is not None else None, "buyer_name": item.buyer.name if item.buyer else None, "buyer_phone": item.buyer.phone if item.buyer else None, "buyer_whatsapp_number": item.buyer.whatsapp_number if item.buyer else None, "buyer_email": item.buyer.email if item.buyer else None})
    return data

def list_properties(db: Session, *, public: bool = False, property_type: str | None = None, status: str | None = None, min_price: float | None = None, max_price: float | None = None, search: str | None = None, sort: str = "newest", page: int = 1, page_size: int = 20) -> dict:
    stmt = select(Property).options(joinedload(Property.images), joinedload(Property.building_details), joinedload(Property.buyer))
    if public and not settings.public_sold_properties:
        stmt = stmt.where(Property.status == "available")
    if property_type:
        stmt = stmt.where(Property.property_type == property_type)
    if status:
        stmt = stmt.where(Property.status == status)
    if min_price is not None:
        stmt = stmt.where(Property.price >= min_price)
    if max_price is not None:
        stmt = stmt.where(Property.price <= max_price)
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(or_(Property.title.ilike(pattern), Property.address.ilike(pattern)))
    stmt = stmt.order_by(Property.price.asc() if sort == "price_asc" else Property.price.desc() if sort == "price_desc" else Property.created_at.asc() if sort == "oldest" else Property.created_at.desc())
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).unique().all()
    return {"items": [property_dict(row, public=public) for row in rows], "page": page, "page_size": page_size, "total": total}

def get_property(db: Session, property_id: int) -> Property | None:
    return db.execute(select(Property).options(joinedload(Property.images), joinedload(Property.building_details), joinedload(Property.buyer)).where(Property.id == property_id)).scalars().unique().first()

def save_property(db: Session, data: PropertyInput, item: Property | None = None) -> Property:
    values = data.model_dump(exclude={"building_details"})
    if item is None:
        item = Property(**values)
        db.add(item)
        db.flush()
    else:
        for key, value in values.items():
            setattr(item, key, value)
        item.updated_at = datetime.now(timezone.utc)
    if data.building_details is None:
        item.building_details = None
    elif item.building_details:
        for key, value in data.building_details.model_dump().items():
            setattr(item.building_details, key, value)
    else:
        item.building_details = BuildingDetail(**data.building_details.model_dump())
    db.commit()
    db.refresh(item)
    return item

def delete_property(db: Session, item: Property) -> None:
    public_ids = [image.public_id for image in item.images if image.public_id]
    db.delete(item)
    db.commit()
    for public_id in public_ids:
        try:
            delete_image(public_id)
        except Exception:
            logger.exception("Could not delete Cloudinary image %s after property deletion", public_id)

def set_sold(db: Session, item: Property, data: SoldInput) -> Property:
    buyer = find_or_create(db, data.buyer_name, data.buyer_phone, data.buyer_whatsapp_number, str(data.buyer_email) if data.buyer_email else None)
    item.buyer = buyer
    item.status = "sold"
    item.sold_at = data.sold_at or datetime.now(timezone.utc)
    item.sale_price = data.sale_price
    item.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return item

def set_available(db: Session, item: Property) -> Property:
    item.status, item.buyer_id, item.sold_at, item.sale_price = "available", None, None, None
    item.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return item
