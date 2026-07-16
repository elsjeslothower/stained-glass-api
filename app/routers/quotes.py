"""Quote endpoints: create, read, patch, and the (stubbed) AI estimate."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/quotes", tags=["quotes"])


def _get_quote_or_404(quote_id: int, db: Session) -> models.Quote:
    quote = db.get(models.Quote, quote_id)
    if quote is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found.")
    return quote


@router.post("", response_model=schemas.QuoteOut, status_code=status.HTTP_201_CREATED)
def create_quote(payload: schemas.QuoteCreate, db: Session = Depends(get_db)):
    if db.get(models.Customer, payload.customer_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found."
        )
    quote = models.Quote(**payload.model_dump())
    db.add(quote)
    db.commit()
    db.refresh(quote)
    return quote


@router.get("", response_model=list[schemas.QuoteOut])
def list_quotes(db: Session = Depends(get_db)):
    return db.scalars(select(models.Quote).order_by(models.Quote.id)).all()


@router.get("/{quote_id}", response_model=schemas.QuoteOut)
def get_quote(quote_id: int, db: Session = Depends(get_db)):
    return _get_quote_or_404(quote_id, db)


@router.patch("/{quote_id}", response_model=schemas.QuoteOut)
def update_quote(
    quote_id: int, payload: schemas.QuoteUpdate, db: Session = Depends(get_db)
):
    """Human-driven edits, including the deliberate status change to 'sent'."""
    quote = _get_quote_or_404(quote_id, db)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(quote, field, value)
    db.commit()
    db.refresh(quote)
    return quote


@router.post("/{quote_id}/estimate", response_model=schemas.QuoteOut)
def estimate_quote(quote_id: int, db: Session = Depends(get_db)):
    """Generate an AI first-pass estimate for this quote.

    NOT YET IMPLEMENTED. When built, this must:
      1. Load the quote's image_url + description
      2. Call the Anthropic API (vision model) for structured JSON:
         piece_count_estimate, sq_inches_estimate, colors_detected,
         complexity_score (1-5), price_low, price_high
      3. Parse defensively (strip markdown fences/prose before json.loads)
      4. Store parsed fields AND the verbatim raw response (ai_raw_response)
      5. Leave status as 'draft' — never auto-advance to 'sent'
    """
    _get_quote_or_404(quote_id, db)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="AI estimation not implemented yet.",
    )
