# Stained Glass Quote Tool — API

Backend that turns a customer's photo + description of a stained glass
project into a structured, editable price quote. An LLM vision call produces
the first-pass estimate; **a human always reviews before a quote is sent** —
the AI assists, it doesn't replace judgment on pricing.

Built for a real small stained-glass business. Portfolio project 2 of 4
(backend/API focus).

## The engineering point

The interesting problem isn't "call an LLM" — it's constraining that call's
output into something a business can trust:

- The model is asked for **structured JSON fields** (piece count, square
  inches, colors, complexity 1–5, price range), parsed defensively.
- The **verbatim raw response is stored alongside** the parsed fields
  (`quotes.ai_raw_response`) so every estimate is auditable.
- The estimate endpoint **never changes quote status** — moving a quote to
  `sent` is a separate, deliberate human action via `PATCH /quotes/{id}`.

## Stack

- FastAPI + SQLAlchemy 2.0 + Postgres
- Anthropic API (Claude, vision-capable) for estimates
- Deploy target (planned): Railway or Fly.io (API), Supabase or Railway (Postgres)

## Setup (Windows-friendly)

```powershell
# 1. Create and activate a virtualenv
python -m venv .venv
.venv\Scripts\activate        # (macOS/Linux: source .venv/bin/activate)

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env        # (macOS/Linux: cp .env.example .env)
# then edit .env with your real DATABASE_URL and ANTHROPIC_API_KEY

# 4. Create the schema (needs a running Postgres and psql on PATH)
psql "<your DATABASE_URL>" -f schema.sql

# 5. Run the API
uvicorn app.main:app --reload
```

Interactive docs at http://127.0.0.1:8000/docs once running.
Health check: `GET /health`.

## Endpoints

| Method | Path                             | Notes                                  |
| ------ | -------------------------------- | -------------------------------------- |
| POST   | /customers                       | Create customer                        |
| GET    | /customers                       | List customers                         |
| GET    | /customers/{id}                  | Get one customer                       |
| POST   | /quotes                          | Create quote (draft)                   |
| GET    | /quotes                          | List quotes                            |
| GET    | /quotes/{id}                     | Get one quote (incl. line items)       |
| PATCH  | /quotes/{id}                     | Edit quote; humans change status here  |
| POST   | /quotes/{id}/estimate            | Vision call → structured estimate      |
| POST   | /quotes/{id}/line-items          | Add line item                          |
| GET    | /quotes/{id}/line-items          | List line items                        |

## Architecture notes

- `app/config.py` — settings via pydantic-settings, reads `.env`
- `app/database.py` — engine, `SessionLocal`, `get_db()` dependency
- `app/models.py` — ORM models; **kept manually in sync with `schema.sql`**
  (no Alembic yet — deliberate; add migrations only if schema churn hurts)
- `app/schemas.py` — Pydantic request/response models
- `app/routers/` — one file per resource

## Roadmap checklist

**Week 1 — CRUD skeleton**
- [x] Schema: customers, quotes, line_items
- [x] CRUD endpoints for all three resources
- [x] `/health` endpoint
- [ ] ⚠️ First-run verification: `pip install`, run `schema.sql` against a
      real Postgres, boot uvicorn, smoke-test each endpoint via /docs.
      **Code is syntax-checked but has never been executed — do this before
      building anything else.**

**Week 2 — AI estimate**
- [x] Implement `POST /quotes/{id}/estimate` — vision call via
      `app/services/ai_estimate.py`, wired into `app/routers/quotes.py`
- [x] Defensive JSON parsing (strips markdown fences / surrounding prose,
      validates required fields, types, and value ranges)
- [x] Tests: happy path + malformed-JSON-from-model path
      (`tests/test_ai_estimate.py`, Anthropic call mocked — no API cost)
- [ ] ⚠️ Not yet run against the real Anthropic API — parsing logic is
      unit-tested with mocks, but the actual vision call has never fired.
      First real call will also validate the model correctly reads glass
      photos, which the mocked tests can't tell you.

**Week 3 — Frontend scaffolding**
- Decided: plain HTML + Tailwind (via CDN, no build step) — served directly
  by FastAPI's `StaticFiles`, same origin as the API (no CORS setup needed).
  React was considered and deliberately skipped: this tool's users are
  stained glass sellers doing simple CRUD/form work, not a complex
  client-state app, and React would be scope-creep into the portfolio's
  separate full-stack project.
- Customer creation is **inline** on the new-quote form (pick existing or
  create new, same screen) — one less click for the seller.
- Planned as 4 resumable sessions:
  - [ ] **Session A** — static file serving wired into FastAPI + read-only
        quote list page (customer, status, price range, created date)
  - [ ] **Session B** — new quote form: inline customer create/select +
        description + image URL (still pasted from an external host —
        real file upload is deliberately deferred, see below)
  - [ ] **Session C** — quote detail page: "Run AI Estimate" button,
        editable estimate fields, raw AI response (collapsible), status
        change via existing PATCH endpoint
  - [ ] **Session D** — line items UI + styling/error-state polish

**Deliberately deferred (don't scope-creep into these without discussion)**
- Real image file upload (multipart endpoint + storage) — current workflow
  is paste an externally-hosted image URL
- Auth — still none; do not deploy this publicly before adding it

**Later / explicitly deferred**
- [ ] Auth (none yet — do not deploy publicly before this)
- [ ] Deployment (Railway/Fly.io + Supabase/Railway Postgres)
- [ ] Alembic migrations, if schema churn warrants it

## Process notes

- Small commits; short work sessions — keep tasks resumable
- Update this checklist alongside code changes so context survives sessions
- When in doubt on scope: ship the smaller working version
