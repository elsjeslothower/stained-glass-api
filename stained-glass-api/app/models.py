"""ORM models. Keep in sync with schema.sql (no migration tool yet)."""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str | None] = mapped_column(Text, unique=True)
    phone: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    quotes: Mapped[list["Quote"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )


class Quote(Base):
    __tablename__ = "quotes"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'sent', 'accepted', 'declined')",
            name="quotes_status_check",
        ),
        CheckConstraint(
            "complexity_score BETWEEN 1 AND 5", name="quotes_complexity_check"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )

    description: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text)

    # AI estimate endpoint must never set this to 'sent' — human action only.
    status: Mapped[str] = mapped_column(Text, nullable=False, default="draft")

    # Parsed AI estimate fields
    piece_count_estimate: Mapped[int | None] = mapped_column(Integer)
    sq_inches_estimate: Mapped[float | None] = mapped_column(Numeric(10, 2))
    colors_detected: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    complexity_score: Mapped[int | None] = mapped_column(Integer)
    price_low: Mapped[float | None] = mapped_column(Numeric(10, 2))
    price_high: Mapped[float | None] = mapped_column(Numeric(10, 2))

    # Verbatim model output, kept for auditing.
    ai_raw_response: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    customer: Mapped["Customer"] = relationship(back_populates="quotes")
    line_items: Mapped[list["LineItem"]] = relationship(
        back_populates="quote", cascade="all, delete-orphan"
    )


class LineItem(Base):
    __tablename__ = "line_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="line_items_quantity_check"),
        CheckConstraint("unit_price >= 0", name="line_items_unit_price_check"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quote_id: Mapped[int] = mapped_column(
        ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    quote: Mapped["Quote"] = relationship(back_populates="line_items")
