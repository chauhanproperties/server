from datetime import datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload
from app.models.customer import Customer
from app.models.property import Property
from app.models.query import Query
from app.services.customer_service import find_or_create

def create_query(db: Session, *, name: str, phone: str, whatsapp_number: str, email: str | None, property_id: int | None, message: str | None) -> Query:
    customer = find_or_create(db, name, phone, whatsapp_number, email)
    item = Query(customer=customer, property_id=property_id, message=message)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

def list_queries(db: Session, status: str | None = None, property_id: int | None = None, date_from: datetime | None = None, date_to: datetime | None = None, search: str | None = None, sort: str = "newest", page: int = 1, page_size: int = 20) -> dict:
    stmt = select(Query).join(Query.customer).options(joinedload(Query.customer), joinedload(Query.property))
    if status:
        stmt = stmt.where(Query.status == status)
    if property_id:
        stmt = stmt.where(Query.property_id == property_id)
    if date_from:
        stmt = stmt.where(Query.raised_at >= date_from)
    if date_to:
        stmt = stmt.where(Query.raised_at <= date_to)
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where((Customer.name.ilike(pattern)) | (Customer.phone.ilike(pattern)))
    stmt = stmt.order_by(Query.raised_at.asc() if sort == "oldest" else Query.raised_at.desc())
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).unique().all()
    return {"items": [query_dict(row) for row in rows], "page": page, "page_size": page_size, "total": total}

def query_dict(item: Query) -> dict:
    c, p = item.customer, item.property
    return {"id": item.id, "status": item.status, "message": item.message, "raised_at": item.raised_at, "resolved_at": item.resolved_at,
            "customer": {"id": c.id, "name": c.name, "phone": c.phone, "whatsapp_number": c.whatsapp_number, "email": c.email, "query_count": len(c.queries)} if c else None,
            "property": {"id": p.id, "title": p.title, "property_type": p.property_type, "address": p.address, "price": float(p.price), "status": p.status} if p else None}

def set_query_status(item: Query, resolved: bool) -> Query:
    target = "resolved" if resolved else "new"
    if item.status == target:
        return item
    item.status = target
    item.resolved_at = datetime.now(timezone.utc) if resolved else None
    return item
