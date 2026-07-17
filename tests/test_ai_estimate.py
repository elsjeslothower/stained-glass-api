"""Tests for app.services.ai_estimate.

These test the parsing logic and the generate_estimate() flow directly,
mocking the Anthropic call so no real API access (or cost) is needed.
"""
from unittest.mock import MagicMock, patch

import pytest

from app.services.ai_estimate import AIEstimateError, generate_estimate, parse_estimate_json

CLEAN_JSON = (
    '{"piece_count_estimate": 12, "sq_inches_estimate": 240.5, '
    '"colors_detected": ["blue", "clear"], "complexity_score": 3, '
    '"price_low": 200, "price_high": 350}'
)


class TestParseEstimateJson:
    def test_clean_json_parses(self):
        result = parse_estimate_json(CLEAN_JSON)
        assert result["piece_count_estimate"] == 12
        assert result["colors_detected"] == ["blue", "clear"]
        assert result["complexity_score"] == 3

    def test_json_wrapped_in_markdown_fences_and_prose(self):
        wrapped = f"Sure, here's the estimate:\n```json\n{CLEAN_JSON}\n```\nLet me know!"
        result = parse_estimate_json(wrapped)
        assert result["piece_count_estimate"] == 12

    def test_malformed_json_raises(self):
        with pytest.raises(AIEstimateError, match="not valid JSON"):
            parse_estimate_json("this is not json")

    def test_missing_field_raises(self):
        missing = (
            '{"piece_count_estimate": 12, "sq_inches_estimate": 240.5, '
            '"colors_detected": ["blue"], "complexity_score": 3}'
        )
        with pytest.raises(AIEstimateError, match="missing fields"):
            parse_estimate_json(missing)

    def test_complexity_out_of_range_raises(self):
        bad = CLEAN_JSON.replace('"complexity_score": 3', '"complexity_score": 9')
        with pytest.raises(AIEstimateError, match="out of range"):
            parse_estimate_json(bad)

    def test_price_low_above_price_high_raises(self):
        bad = CLEAN_JSON.replace('"price_low": 200', '"price_low": 999')
        with pytest.raises(AIEstimateError, match="exceeds price_high"):
            parse_estimate_json(bad)


class TestGenerateEstimate:
    @patch("app.services.ai_estimate._call_claude")
    def test_happy_path_returns_parsed_and_raw(self, mock_call_claude):
        mock_call_claude.return_value = CLEAN_JSON

        parsed, raw = generate_estimate("https://example.com/photo.jpg", "A rose window")

        assert parsed is not None
        assert parsed["piece_count_estimate"] == 12
        assert raw == CLEAN_JSON

    @patch("app.services.ai_estimate._call_claude")
    def test_malformed_model_response_returns_none_but_keeps_raw(self, mock_call_claude):
        garbled = "I'm not able to provide that in JSON format right now, sorry!"
        mock_call_claude.return_value = garbled

        parsed, raw = generate_estimate("https://example.com/photo.jpg", "A rose window")

        # Parsing failed -> None, but the raw text must still be returned
        # so the caller can store it on the quote for auditing.
        assert parsed is None
        assert raw == garbled
