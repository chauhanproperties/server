from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload
from app.core.dependencies import require_admin
from app.database import get_db
from app.models.query import Query
from app.models.property import Property
from app.services.email_service import send_email
from app.services.query_service import list_queries, query_dict, set_query_status
from app.services.whatsapp_service import build_link
from app.schemas.query import EmailReply

router = APIRouter(prefix="/api/admin/queries", tags=["admin queries"], dependencies=[Depends(require_admin)])

@router.get("/stats")
def query_stats(db: Session = Depends(get_db)):
    counts = dict(db.execute(select(Query.status, func.count(Query.id)).group_by(Query.status)).all())
    average = db.scalar(select(func.avg(func.extract("epoch", Query.resolved_at - Query.raised_at))).where(Query.resolved_at.is_not(None))) or 0
    by_property = db.execute(select(Property.id, Property.title, func.count(Query.id)).outerjoin(Query, Query.property_id == Property.id).group_by(Property.id, Property.title).order_by(func.count(Query.id).desc()).limit(10)).all()
    return {"new": counts.get("new", 0), "resolved": counts.get("resolved", 0), "average_resolution_seconds": float(average), "queries_per_property": [{"property_id": row[0], "title": row[1], "count": row[2]} for row in by_property]}

@router.get("")
def queries(status: str | None = None, property_id: int | None = None, date_from: datetime | None = None, date_to: datetime | None = None, search: str | None = None, sort: str = "newest", page: int = QueryParam(1, ge=1), page_size: int = QueryParam(20, ge=1, le=100), db: Session = Depends(get_db)):
    if status and status not in {"new", "resolved"}:
        raise HTTPException(422, "Invalid query status")
    return list_queries(db, status=status, property_id=property_id, date_from=date_from, date_to=date_to, search=search, sort=sort, page=page, page_size=page_size)

@router.get("/{query_id}")
def get_query(query_id: int, db: Session = Depends(get_db)):
    item = db.scalar(select(Query).options(joinedload(Query.customer), joinedload(Query.property)).where(Query.id == query_id))
    if not item:
        raise HTTPException(404, "Query not found")
    return query_dict(item)

@router.patch("/{query_id}/resolve")
def resolve(query_id: int, db: Session = Depends(get_db)):
    item = db.get(Query, query_id)
    if not item:
        raise HTTPException(404, "Query not found")
    item = set_query_status(item, True)
    db.commit()
    return {"message": "Query marked resolved.", "status": item.status, "resolved_at": item.resolved_at}

@router.patch("/{query_id}/reopen")
def reopen(query_id: int, db: Session = Depends(get_db)):
    item = db.get(Query, query_id)
    if not item:
        raise HTTPException(404, "Query not found")
    item = set_query_status(item, False)
    db.commit()
    return {"message": "Query reopened.", "status": item.status, "resolved_at": item.resolved_at}

@router.post("/{query_id}/reply-email")
def reply_email(query_id: int, data: EmailReply, db: Session = Depends(get_db)):
    item = db.scalar(select(Query).options(joinedload(Query.customer)).where(Query.id == query_id))
    if not item:
        raise HTTPException(404, "Query not found")
    if not item.customer.email:
        raise HTTPException(409, "This customer has no email address on file.")
    try:
        send_email(item.customer.email, data.subject, data.body)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from None
    return {"message": "Email sent."}

@router.get("/{query_id}/whatsapp-link")
def whatsapp_link(query_id: int, message: str, db: Session = Depends(get_db)):
    item = db.scalar(select(Query).options(joinedload(Query.customer)).where(Query.id == query_id))
    if not item:
        raise HTTPException(404, "Query not found")
    return {"url": build_link(item.customer.whatsapp_number, message)}
