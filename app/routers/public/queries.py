from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.rate_limit import client_ip, enforce_rate_limit
from app.models.property import Property
from app.schemas.query import QueryCreate
from app.services.query_service import create_query

router = APIRouter(prefix="/api/public/queries", tags=["public queries"])
@router.post("")
def submit(data: QueryCreate, request: Request, db: Session = Depends(get_db)):
    enforce_rate_limit(client_ip(request), scope="public-enquiries", limit=5, window_seconds=3600,
                       message="Too many enquiries were sent from this network. Please try again later.")
    if data.property_id and not db.get(Property, data.property_id):
        raise HTTPException(404, "Property not found")
    try:
        item = create_query(db, name=data.name, phone=data.phone, whatsapp_number=data.whatsapp_number, email=str(data.email) if data.email else None, property_id=data.property_id, message=data.message)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    return {"id": item.id, "status": item.status, "message": "Thank you. Your enquiry has been received."}
