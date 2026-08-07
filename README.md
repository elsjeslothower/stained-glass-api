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
- Deploy target: Railway (API) + Supabase (Postgres), custom domain
  `api.elsje.codes` — see "Deployment" below

## Setup (Windows-friendly)

```powershell
# 1. Create and activate a virtualenv
python -m venv .venv
.venv\Scripts\activate        # (macOS/Linux: source .venv/bin/activate)

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env        # (macOS/Linux: cp .env.example .env)
# then edit .env with your real DATABASE_URL and ANTHROPIC_API_KEY, and set
# an admin login (see "Auth" below) — all four ADMIN_*/SESSION_* keys are
# required, the app won't start without them.

# 4. Create the schema (needs a running Postgres and psql on PATH)
psql "<your DATABASE_URL>" -f schema.sql

# 5. Run the API
uvicorn app.main:app --reload
```

Interactive docs at http://127.0.0.1:8000/docs once running.
Health check: `GET /health` (the only unauthenticated route besides `/auth/*`).

## Auth

Single admin login, no users table — see `app/auth.py`. One-off setup:

```bash
# Password hash for ADMIN_PASSWORD_HASH — never store the plaintext password
python -c "import bcrypt; print(bcrypt.hashpw(b'yourpassword', bcrypt.gensalt()).decode())"

# Session-signing secret for SESSION_SECRET_KEY — rotating this logs everyone out
python -c "import secrets; print(secrets.token_hex(32))"
```

Put both, plus `ADMIN_USERNAME`, `CORS_ORIGINS`, and `SESSION_COOKIE_SECURE`,
in `.env` (see `.env.example` for the full set with comments). The frontend
logs in via `POST /auth/login`, which sets an `HttpOnly` session cookie —
every page but `login.html` redirects there if the session is missing or
expired.

## Frontend

Static, no build step — open directly or serve with any static file server:

```powershell
cd frontend
python -m http.server 5500
# then open http://127.0.0.1:5500/index.html — you'll be bounced to
# login.html first if there's no active session
```

It talks to the API at `http://127.0.0.1:8000` by default; change the "API
base" field in the header (persisted in `localStorage`) to point elsewhere.
Whatever origin you serve `frontend/` from must be listed in the API's
`CORS_ORIGINS` env var, or login will fail silently (cookie won't be set).

## Deployment

API on Railway, Postgres on Supabase, custom domain `api.elsje.codes`. The
frontend is a separate static drop-in served from the portfolio site at
`elsje.codes/quote-tool/` (a copy of `frontend/`, not this repo's concern to
deploy) — `api.elsje.codes` and `elsje.codes` share a registrable domain, so
the session cookie stays same-site (`SameSite=Lax`, no code change needed
for the cross-subdomain case).

- **Start command:** `Procfile` (`web: uvicorn app.main:app --host 0.0.0.0
  --port $PORT`) — Railway's Nixpacks auto-detects it.
- **Database:** Supabase's **Session Pooler** connection (port 5432, host
  `aws-<region>.pooler.supabase.com`), not the direct connection
  (`db.<ref>.supabase.co:5432`) and not the Transaction Pooler (port 6543).
  Supabase's direct-connection host is **IPv6-only** — confirmed the hard
  way, `psql` couldn't resolve/route to it from this network — so the
  Session Pooler is actually required here, not just a nice-to-have. It's
  IPv4-compatible and, unlike the Transaction Pooler, supports session-level
  features SQLAlchemy relies on. Append `?sslmode=require` to the
  connection string.
- **Env vars to set in Railway's dashboard** (never commit these):

  | Env var | Value |
  | --- | --- |
  | `DATABASE_URL` | Supabase Session Pooler connection string + `?sslmode=require` |
  | `ANTHROPIC_API_KEY` | real key |
  | `ADMIN_USERNAME` | admin username |
  | `ADMIN_PASSWORD_HASH` | bcrypt hash (see "Auth" above) |
  | `SESSION_SECRET_KEY` | a **fresh** `secrets.token_hex(32)` — don't reuse the local `.env` value |
  | `CORS_ORIGINS` | `https://elsje.codes` (origin only; `/quote-tool/` path doesn't matter for CORS matching) |
  | `SESSION_COOKIE_SECURE` | `true` |

  `PORT` is injected by Railway automatically.
- **Custom domain:** add `api.elsje.codes` under Railway → Networking, then
  add the CNAME Railway shows at whatever registrar hosts `elsje.codes`'s
  DNS.
- **Schema:** run `psql "<DATABASE_URL>?sslmode=require" -f schema.sql`
  against the new Supabase database once, before the first deploy — same as
  local setup, just pointed at Supabase instead of localhost.

## Endpoints

| Method | Path                             | Notes                                  |
| ------ | -------------------------------- | -------------------------------------- |
| POST   | /auth/login                      | Log in, sets session cookie            |
| POST   | /auth/logout                     | Clear session                          |
| GET    | /auth/me                         | Current session's username (401 if none) |
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
- [x] First-run verification: installed deps, ran `schema.sql` against a
      real local Postgres, booted uvicorn, smoke-tested every endpoint
      (`POST`/`GET`/`PATCH` on customers, quotes, line items — including a
      404 and a validation-error case). One real bug found and fixed along
      the way: the installed `anthropic` package was corrupted (missing
      `anthropic.types.shared` on disk), which crashed the app at import
      time before uvicorn could even bind the port — reinstalling the
      package fixed it. Not a code issue, but worth knowing if this
      environment gets rebuilt from `requirements.txt` again.

**Week 2 — AI estimate**
- [x] Implement `POST /quotes/{id}/estimate` — vision call via
      `app/services/ai_estimate.py`, wired into `app/routers/quotes.py`
- [x] Defensive JSON parsing (strips markdown fences / surrounding prose,
      validates required fields, types, and value ranges)
- [x] Tests: happy path + malformed-JSON-from-model path
      (`tests/test_ai_estimate.py`, Anthropic call mocked — no API cost)
- [x] Verified against the real Anthropic API: correctly rejected a
      mismatched placeholder photo (returned a safe validation error
      instead of a fabricated estimate), then returned a reasonable
      structured estimate on a real stained-glass sketch.

**Week 3 — Frontend scaffolding**
- [x] Plain HTML/Tailwind (CDN, no build step) — faster than React for a
      backend-focused portfolio project. Lives in `frontend/`:
      `index.html` (quote list + new quote form), `customers.html`
      (customer list + create form), `quote.html` (quote detail: editable
      estimate fields, "Run AI estimate", line items, "Send quote" action).
- [x] CORS enabled on the API (`app/main.py`) so the static frontend can
      call it from a different origin — wide open for now since there's no
      auth yet; tighten before any public deployment.
- [x] Verified against the real FastAPI + Postgres backend (not just the
      mock server used earlier): served `frontend/` statically, pointed it
      at a locally running API, and confirmed the quote list, customer
      list, and quote detail pages all render real data correctly —
      including the actual customer, the real AI estimate fields, colors,
      and the quote's real image loading in the preview. Also exercised
      create/patch/line-item/send against the live API directly, then
      cleaned up the test rows afterward.

**Week 4 — Auth**
- [x] Single-admin session auth: `app/auth.py` (`bcrypt` password check,
      `require_auth` dependency), `app/routers/auth.py` (`/auth/login`,
      `/auth/logout`, `/auth/me`). No users table — one credential from
      `.env`, proportionate to a solo-owner tool. Deliberately deferred:
      multi-user support, password self-service, login rate-limiting,
      explicit CSRF tokens (covered by the CORS allowlist + `SameSite=Lax`
      for now), a revocable server-side session store.
- [x] `customers`, `quotes`, `line_items` routers protected via
      `dependencies=[Depends(require_auth)]` at `include_router()` — zero
      changes to the route files themselves. `/health` and `/auth/*` stay
      public.
- [x] CORS tightened: `allow_origins` is now a configurable allowlist
      (`CORS_ORIGINS`) instead of `"*"`, with `allow_credentials=True` so
      the session cookie can flow cross-origin during local dev.
- [x] Frontend: `login.html`, `requireAuth()`/`logout()` in `api.js`,
      every other page guards its startup on `requireAuth()` and gets a
      "Log out" link in the header.
- [x] Verified against the real backend: curl'd the full cycle (401 before
      login → login sets cookie → authenticated reads succeed → logout →
      401 again), then confirmed the same in the browser — unauthenticated
      visits redirect to `login.html`, a real login persists across all
      three pages, and logging out re-locks the app.

**Week 5 — Deployment (in progress)**
- [x] Stack decided: Railway (API) + Supabase (Postgres), custom domain
      `api.elsje.codes` so the session cookie stays same-site with
      `elsje.codes` — no `SameSite`/`Secure` code change needed, see
      "Deployment" above.
- [x] `Procfile` added for Railway's Nixpacks to find the start command.
- [x] Supabase project created, `schema.sql` run against it (via the Session
      Pooler connection — the direct connection is IPv6-only and wasn't
      reachable from this network, see "Deployment" above)
- [x] Frontend dropped in at `elsje.codes/quote-tool/` (separate repo,
      committed on a branch there, not yet pushed to `master`)
- [ ] Railway project created, env vars set, custom domain + DNS CNAME live
- [ ] End-to-end verified against the live stack (see Deployment section);
      flip this whole entry to done only once that passes

**Later / explicitly deferred**
- [ ] Alembic migrations, if schema churn warrants it
- [ ] Move quote images from pasted URLs to owned object storage (Supabase
      Storage, once on Supabase) — `image_url` would store a storage
      key/reference instead of a third-party link

## Process notes

- Small commits; short work sessions — keep tasks resumable
- Update this checklist alongside code changes so context survives sessions
- When in doubt on scope: ship the smaller working version
