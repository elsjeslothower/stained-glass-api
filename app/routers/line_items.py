"""Line item endpoints, nested under a quote."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/quotes/{quote_id}/line-items", tags=["line-items"])


def _ensure_quote_exists(quote_id: int, db: Session) -> None:
    if db.get(models.Quote, quote_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found.")


@router.post("", response_model=schemas.LineItemOut, status_code=status.HTTP_201_CREATED)
def create_line_item(
    quote_id: int, payload: schemas.LineItemCreate, db: Session = Depends(get_db)
):
    _ensure_quote_exists(quote_id, db)
    item = models.LineItem(quote_id=quote_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("", response_model=list[schemas.LineItemOut])
def list_line_items(quote_id: int, db: Session = Depends(get_db)):
    _ensure_quote_exists(quote_id, db)
    return db.scalars(
        select(models.LineItem)
        .where(models.LineItem.quote_id == quote_id)
        .order_by(models.LineItem.id)
    ).all()
