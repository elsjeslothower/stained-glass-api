"""FastAPI application entry point.

Run locally:
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import customers, line_items, quotes

app = FastAPI(
    title="Stained Glass Quote Tool API",
    description=(
        "Turns a customer's photo + description of a stained glass project "
        "into a structured, editable price quote. AI provides a first-pass "
        "estimate; a human always reviews before anything is sent."
    ),
    version="0.1.0",
)

# No auth yet (see README), so this is wide open for local frontend dev.
# Tighten to specific origins before any public deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(customers.router)
app.include_router(quotes.router)
app.include_router(line_items.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
