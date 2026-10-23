import logging

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload
from app.core.dependencies import require_admin
from app.database import get_db
from app.models.customer import Customer
from app.models.property import Property
from app.models.query import Query
from app.services.query_service import query_counts, query_dict

router = APIRouter(prefix="/api/admin", tags=["admin dashboard"], dependencies=[Depends(require_admin)])
logger = logging.getLogger(__name__)

@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    def safe(read, fallback=None):
        try:
            return read()
        except Exception:
            logger.exception("Dashboard data query failed")
            db.rollback()
            return fallback

    def count(model, condition=None):
        statement = select(func.count(model.id))
        if condition is not None:
            statement = statement.where(condition)
        return safe(lambda: db.scalar(statement))

    average = safe(
        lambda: db.scalar(
            select(func.avg(func.extract("epoch", Query.resolved_at - Query.raised_at))).where(Query.resolved_at.is_not(None))
        )
    )
    latest = safe(lambda: db.scalars(select(Query).options(joinedload(Query.customer), joinedload(Query.property)).where(Query.status == "new").order_by(Query.raised_at.desc()).limit(8)).unique().all())
    counts = safe(lambda: query_counts(db, [item.customer_id for item in latest])) if latest is not None else {}
    if counts is None:
        counts = {}
    latest_items = safe(lambda: [query_dict(item, counts.get(item.customer_id, 0)) for item in latest]) if latest is not None else None
    return {
        "new_queries": count(Query, Query.status == "new"),
        "resolved_queries": count(Query, Query.status == "resolved"),
        "available_properties": count(Property, Property.status == "available"),
        "sold_properties": count(Property, Property.status == "sold"),
        "total_customers": count(Customer),
        "average_resolution_seconds": float(average) if average is not None else None,
        "latest_new_queries": latest_items,
    }
