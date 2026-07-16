"""FastAPI application entry point.

Run locally:
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI

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

app.include_router(customers.router)
app.include_router(quotes.router)
app.include_router(line_items.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
