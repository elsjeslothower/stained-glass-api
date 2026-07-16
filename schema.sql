-- Stained Glass Quote Tool — Postgres schema
-- Run once against a fresh database:
--   psql "$DATABASE_URL" -f schema.sql
-- (SQLAlchemy models in app/models.py mirror this schema. If you change one,
--  change the other — there is no migration tool yet; Alembic is a later task.)

CREATE TABLE customers (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    email       TEXT UNIQUE,
    phone       TEXT,
    notes       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE quotes (
    id                   SERIAL PRIMARY KEY,
    customer_id          INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,

    -- Customer-provided inputs
    description          TEXT NOT NULL,
    image_url            TEXT,

    -- Lifecycle. The AI estimate endpoint must NEVER move this to 'sent';
    -- only a human via PATCH /quotes/{id} does that.
    status               TEXT NOT NULL DEFAULT 'draft'
                         CHECK (status IN ('draft', 'sent', 'accepted', 'declined')),

    -- AI first-pass estimate (parsed, structured fields)
    piece_count_estimate INTEGER,
    sq_inches_estimate   NUMERIC(10, 2),
    colors_detected      TEXT[],
    complexity_score     INTEGER CHECK (complexity_score BETWEEN 1 AND 5),
    price_low            NUMERIC(10, 2),
    price_high           NUMERIC(10, 2),

    -- Full raw model response, kept verbatim for auditing/debugging.
    ai_raw_response      TEXT,

    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE line_items (
    id           SERIAL PRIMARY KEY,
    quote_id     INTEGER NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
    description  TEXT NOT NULL,
    quantity     INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    unit_price   NUMERIC(10, 2) NOT NULL CHECK (unit_price >= 0),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_quotes_customer_id ON quotes(customer_id);
CREATE INDEX idx_line_items_quote_id ON line_items(quote_id);
