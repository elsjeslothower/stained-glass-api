"""Pydantic request/response schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

QuoteStatus = Literal["draft", "sent", "accepted", "declined"]


# ---------- Customers ----------

class CustomerCreate(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr | None = None
    phone: str | None = None
    notes: str | None = None


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str | None
    phone: str | None
    notes: str | None
    created_at: datetime


# ---------- Line items ----------

class LineItemCreate(BaseModel):
    description: str = Field(min_length=1)
    quantity: int = Field(default=1, gt=0)
    unit_price: Decimal = Field(ge=0)


class LineItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quote_id: int
    description: str
    quantity: int
    unit_price: Decimal
    created_at: datetime


# ---------- Quotes ----------

class QuoteCreate(BaseModel):
    customer_id: int
    description: str = Field(min_length=1)
    image_url: str | None = None


class QuoteUpdate(BaseModel):
    """PATCH body — all fields optional; only provided ones are applied.

    Note: status changes (e.g. draft -> sent) happen here, deliberately as a
    human-driven action, never inside the AI estimate endpoint.
    """

    description: str | None = None
    image_url: str | None = None
    status: QuoteStatus | None = None
    piece_count_estimate: int | None = None
    sq_inches_estimate: Decimal | None = None
    colors_detected: list[str] | None = None
    complexity_score: int | None = Field(default=None, ge=1, le=5)
    price_low: Decimal | None = None
    price_high: Decimal | None = None


class QuoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    description: str
    image_url: str | None
    status: QuoteStatus
    piece_count_estimate: int | None
    sq_inches_estimate: Decimal | None
    colors_detected: list[str] | None
    complexity_score: int | None
    price_low: Decimal | None
    price_high: Decimal | None
    ai_raw_response: str | None
    created_at: datetime
    updated_at: datetime
    line_items: list[LineItemOut] = []
