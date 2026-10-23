from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload
from app.core.dependencies import require_admin
from app.database import get_db
from app.models.customer import Customer
from app.models.query import Query
from app.models.property import Property
from app.schemas.customer import CustomerUpdate

router = APIRouter(prefix="/api/admin/customers", tags=["admin customers"], dependencies=[Depends(require_admin)])

@router.get("")
def list_customers(search: str | None = None, page: int = QueryParam(1, ge=1), page_size: int = QueryParam(20, ge=1, le=100), db: Session = Depends(get_db)):
    stmt = select(Customer)
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(or_(Customer.name.ilike(pattern), Customer.phone.ilike(pattern), Customer.email.ilike(pattern)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(Customer.registered_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    ids = [c.id for c in rows]
    counts = dict(db.execute(select(Query.customer_id, func.count(Query.id)).where(Query.customer_id.in_(ids)).group_by(Query.customer_id)).all()) if ids else {}
    return {"items": [{"id": c.id, "name": c.name, "phone": c.phone, "whatsapp_number": c.whatsapp_number, "email": c.email, "age": c.age, "gender": c.gender, "registered_at": c.registered_at, "query_count": counts.get(c.id, 0)} for c in rows], "page": page, "page_size": page_size, "total": total}

@router.get("/{customer_id}")
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.scalar(select(Customer).options(joinedload(Customer.queries).joinedload(Query.property), joinedload(Customer.purchases)).where(Customer.id == customer_id))
    if not customer:
        raise HTTPException(404, "Customer not found")
    return {"id": customer.id, "name": customer.name, "phone": customer.phone, "whatsapp_number": customer.whatsapp_number, "email": customer.email, "age": customer.age, "gender": customer.gender, "registered_at": customer.registered_at,
            "queries": [{"id": q.id, "status": q.status, "message": q.message, "raised_at": q.raised_at, "resolved_at": q.resolved_at, "property_title": q.property.title if q.property else None} for q in sorted(customer.queries, key=lambda q: q.raised_at, reverse=True)],
            "purchases": [{"id": p.id, "title": p.title, "status": p.status, "sold_at": p.sold_at, "sale_price": float(p.sale_price) if p.sale_price is not None else None} for p in customer.purchases]}

@router.patch("/{customer_id}")
def update_customer(customer_id: int, data: CustomerUpdate, db: Session = Depends(get_db)):
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(404, "Customer not found")
    if data.gender not in {None, "male", "female", "other"}:
        raise HTTPException(422, "Gender must be male, female, other, or empty.")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(customer, key, str(value) if key == "email" and value else value)
    db.commit()
    return {"message": "Customer updated."}
