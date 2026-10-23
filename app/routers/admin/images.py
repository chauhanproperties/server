import logging
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.config import settings
from app.core.dependencies import require_admin
from app.database import get_db
from app.models.property import Property
from app.models.property_image import PropertyImage
from app.services.image_service import delete_image, upload_image

router = APIRouter(prefix="/api/admin/properties/{property_id}/images", tags=["admin images"], dependencies=[Depends(require_admin)])
logger = logging.getLogger(__name__)

class OrderInput(BaseModel):
    image_ids: list[int]

@router.post("")
def upload_images(property_id: int, files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    item = db.get(Property, property_id)
    if not item:
        raise HTTPException(404, "Property not found")
    count = len(item.images)
    if count + len(files) > settings.max_image_count:
        raise HTTPException(422, f"A property can have at most {settings.max_image_count} images.")
    made = []
    try:
        highest_order = db.scalar(select(func.max(PropertyImage.display_order)).where(PropertyImage.property_id == property_id))
        next_order = (highest_order + 1) if highest_order is not None else 0
        for file in files:
            data = file.file.read(settings.max_image_bytes + 1)
            result = upload_image(data, file.content_type)
            image = PropertyImage(property_id=property_id, image_url=result["secure_url"], public_id=result["public_id"], display_order=next_order)
            db.add(image)
            made.append((image, result["public_id"]))
            next_order += 1
        db.commit()
        return [{"id": image.id, "image_url": image.image_url, "public_id": image.public_id, "display_order": image.display_order} for image, _ in made]
    except ValueError as exc:
        db.rollback()
        for _, public_id in made:
            try:
                delete_image(public_id)
            except Exception:
                logger.exception("Could not clean up Cloudinary image %s after upload validation failure", public_id)
        raise HTTPException(422, str(exc)) from None
    except Exception:
        db.rollback()
        for _, public_id in made:
            try:
                delete_image(public_id)
            except Exception:
                logger.exception("Could not clean up Cloudinary image %s after upload failure", public_id)
        raise HTTPException(502, "Image upload failed. The property was saved; try the upload again.") from None

@router.get("")
def list_images(property_id: int, db: Session = Depends(get_db)):
    if not db.get(Property, property_id):
        raise HTTPException(404, "Property not found")
    return [{"id": x.id, "image_url": x.image_url, "public_id": x.public_id, "display_order": x.display_order} for x in db.scalars(select(PropertyImage).where(PropertyImage.property_id == property_id).order_by(PropertyImage.display_order))]

@router.delete("/{image_id}", status_code=204)
def remove_image(property_id: int, image_id: int, db: Session = Depends(get_db)):
    image = db.scalar(select(PropertyImage).where(PropertyImage.id == image_id, PropertyImage.property_id == property_id))
    if not image:
        raise HTTPException(404, "Image not found")
    try:
        delete_image(image.public_id)
    except Exception:
        raise HTTPException(502, "The image could not be deleted from storage. Try again.") from None
    db.delete(image)
    db.commit()

@router.put("/order")
def reorder_images(property_id: int, data: OrderInput, db: Session = Depends(get_db)):
    if not db.get(Property, property_id):
        raise HTTPException(404, "Property not found")
    images = list(db.scalars(select(PropertyImage).where(PropertyImage.property_id == property_id)))
    if len(data.image_ids) != len(images) or set(data.image_ids) != {x.id for x in images}:
        raise HTTPException(422, "Send every image ID once to set the order.")
    by_id = {x.id: x for x in images}
    for index, image_id in enumerate(data.image_ids):
        by_id[image_id].display_order = index
    db.commit()
    return {"message": "Image order saved."}
