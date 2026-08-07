"""FastAPI application entry point.

Run locally:
    uvicorn app.main:app --reload
"""

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.auth import require_auth
from app.config import get_settings
from app.routers import auth, customers, line_items, quotes

settings = get_settings()

app = FastAPI(
    title="Stained Glass Quote Tool API",
    description=(
        "Turns a customer's photo + description of a stained glass project "
        "into a structured, editable price quote. AI provides a first-pass "
        "estimate; a human always reviews before anything is sent."
    ),
    version="0.1.0",
)

# Session must be added before CORS so CORS ends up outermost (Starlette
# wraps the last-added middleware around earlier ones) and can handle
# preflight OPTIONS requests cleanly.
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret_key,
    session_cookie="sg_session",
    same_site="lax",
    https_only=settings.session_cookie_secure,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(customers.router, dependencies=[Depends(require_auth)])
app.include_router(quotes.router, dependencies=[Depends(require_auth)])
app.include_router(line_items.router, dependencies=[Depends(require_auth)])


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
