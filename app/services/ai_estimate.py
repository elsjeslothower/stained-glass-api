"""AI-powered first-pass estimate generation.

Isolated from the router so the "call Claude, parse the result" logic can be
unit tested without needing a live FastAPI request/DB session.
"""

import base64
import json
import re

import httpx
from anthropic import Anthropic

from app.config import get_settings

MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = (
    "You are helping a stained glass artist produce a first-pass price "
    "estimate from a customer's photo and description. Respond with ONLY "
    "a single JSON object — no prose before or after, no markdown code "
    "fences. The JSON object must have exactly these keys:\n"
    '  "piece_count_estimate": integer, estimated number of individual glass pieces\n'
    '  "sq_inches_estimate": number, estimated total square inches of glass\n'
    '  "colors_detected": array of strings, distinct colors visible\n'
    '  "complexity_score": integer from 1 (simple geometric) to 5 (highly detailed/curved)\n'
    '  "price_low": number, low end of a fair price estimate in USD\n'
    '  "price_high": number, high end of a fair price estimate in USD\n'
    "This is a first-pass estimate only — a human will review it before "
    "any quote is sent to a customer."
)

REQUIRED_FIELDS = {
    "piece_count_estimate",
    "sq_inches_estimate",
    "colors_detected",
    "complexity_score",
    "price_low",
    "price_high",
}

_SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


class AIEstimateError(Exception):
    """Raised when the estimate call or its parsing fails."""


def _fetch_image_as_base64(image_url: str) -> tuple[str, str]:
    """Download the quote's image and return (base64_data, media_type)."""
    try:
        response = httpx.get(image_url, timeout=15.0, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise AIEstimateError(f"Could not download image_url: {exc}") from exc

    media_type = response.headers.get("content-type", "").split(";")[0].strip()
    if media_type not in _SUPPORTED_IMAGE_TYPES:
        # Best-effort fallback; Claude will reject it if it's genuinely not an image.
        media_type = "image/jpeg"

    data = base64.standard_b64encode(response.content).decode("utf-8")
    return data, media_type


def _call_claude(image_url: str, description: str) -> str:
    """Make the vision API call and return the raw text response."""
    settings = get_settings()
    client = Anthropic(api_key=settings.anthropic_api_key)

    image_data, media_type = _fetch_image_as_base64(image_url)

    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": f"Customer's project description: {description}",
                        },
                    ],
                }
            ],
        )
    except Exception as exc:  # anthropic SDK raises several distinct error types
        raise AIEstimateError(f"Anthropic API call failed: {exc}") from exc

    text_blocks = [block.text for block in message.content if block.type == "text"]
    if not text_blocks:
        raise AIEstimateError("Anthropic API returned no text content.")
    return "".join(text_blocks)


def _strip_markdown_fences(raw: str) -> str:
    """Models sometimes wrap JSON in ```json ... ``` fences. Strip if present."""
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", raw, re.DOTALL)
    return fenced.group(1) if fenced else raw


def parse_estimate_json(raw: str) -> dict:
    """Defensively parse the model's response into the expected structure.

    Raises AIEstimateError with a human-readable reason on any failure —
    missing/extra prose, invalid JSON, missing fields, or wrong types.
    """
    candidate = _strip_markdown_fences(raw).strip()

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise AIEstimateError(f"Response was not valid JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise AIEstimateError("Response JSON was not an object.")

    missing = REQUIRED_FIELDS - parsed.keys()
    if missing:
        raise AIEstimateError(f"Response JSON missing fields: {sorted(missing)}")

    try:
        result = {
            "piece_count_estimate": int(parsed["piece_count_estimate"]),
            "sq_inches_estimate": float(parsed["sq_inches_estimate"]),
            "colors_detected": [str(c) for c in parsed["colors_detected"]],
            "complexity_score": int(parsed["complexity_score"]),
            "price_low": float(parsed["price_low"]),
            "price_high": float(parsed["price_high"]),
        }
    except (TypeError, ValueError) as exc:
        raise AIEstimateError(f"Response JSON had wrong field types: {exc}") from exc

    if not (1 <= result["complexity_score"] <= 5):
        raise AIEstimateError(
            f"complexity_score out of range 1-5: {result['complexity_score']}"
        )
    if result["price_low"] > result["price_high"]:
        raise AIEstimateError(
            f"price_low ({result['price_low']}) exceeds price_high "
            f"({result['price_high']})"
        )

    return result


def generate_estimate(image_url: str, description: str) -> tuple[dict | None, str]:
    """Run the full estimate flow.

    Returns (parsed_fields_or_None, raw_response_text). parsed_fields is
    None if parsing failed — the raw text is always returned so the caller
    can store it for auditing even on failure.
    """
    raw = _call_claude(image_url, description)
    try:
        parsed = parse_estimate_json(raw)
    except AIEstimateError:
        return None, raw
    return parsed, raw
