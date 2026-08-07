"""Quote endpoints: create, read, patch, and the (stubbed) AI estimate."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.services.ai_estimate import AIEstimateError, generate_estimate

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

    Calls a vision-capable Claude model with the quote's image + description,
    asking for structured JSON. The raw response is always stored for
    auditing, even if parsing fails. This endpoint never changes `status` —
    moving a quote to 'sent' is a deliberate human action via PATCH.
    """
    quote = _get_quote_or_404(quote_id, db)

    if not quote.image_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quote has no image_url; cannot generate an AI estimate.",
        )

    try:
        parsed, raw_response = generate_estimate(quote.image_url, quote.description)
    except AIEstimateError as exc:
        # The call itself failed (bad image URL, network error, API error).
        # Nothing to store here since we got no response at all.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI estimate call failed: {exc}",
        )

    # Always persist the raw response for auditing, whether or not it parsed.
    quote.ai_raw_response = raw_response

    if parsed is None:
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "AI response could not be parsed into the expected structure. "
                "The raw response has been saved on the quote for review."
            ),
        )

    quote.piece_count_estimate = parsed["piece_count_estimate"]
    quote.sq_inches_estimate = parsed["sq_inches_estimate"]
    quote.colors_detected = parsed["colors_detected"]
    quote.complexity_score = parsed["complexity_score"]
    quote.price_low = parsed["price_low"]
    quote.price_high = parsed["price_high"]
    # status intentionally left untouched — stays 'draft' until a human PATCHes it.

    db.commit()
    db.refresh(quote)
    return quote
