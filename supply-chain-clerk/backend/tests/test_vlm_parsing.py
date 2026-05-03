"""
Unit tests for the VLM prompt and response parsing.
Run: pytest tests/test_vlm_parsing.py -v
"""
import json
import pytest
from app.models.intake_record import IntakeRecord


SAMPLE_RESPONSE = '''
{
  "batch_no":        {"value": "BT-2024-447", "confidence": 0.85},
  "expiry_date":     {"value": "2026-03-01",  "confidence": 0.90},
  "quantity":        {"value": 250,            "confidence": 0.88},
  "supplier_name":   {"value": "Himalaya Herbs", "confidence": 0.95},
  "product_name":    {"value": "Ashwagandha Extract", "confidence": 0.92},
  "unit_of_measure": {"value": "units",        "confidence": 0.80}
}
'''

PARTIAL_RESPONSE = '''
{
  "batch_no":        {"value": "BT-2024-448", "confidence": 0.60},
  "expiry_date":     {"value": null,           "confidence": 0.0},
  "quantity":        {"value": null,           "confidence": 0.0},
  "supplier_name":   {"value": "Unknown",      "confidence": 0.50},
  "product_name":    {"value": "Paracetamol",  "confidence": 0.70},
  "unit_of_measure": {"value": "strips",       "confidence": 0.75}
}
'''


def parse(json_str: str) -> IntakeRecord:
    return IntakeRecord(**json.loads(json_str.strip()))


def test_clean_response_parsed_correctly():
    record = parse(SAMPLE_RESPONSE)
    assert record.batch_no.value == "BT-2024-447"
    assert record.expiry_date.value == "2026-03-01"
    assert record.quantity.value == 250
    assert record.supplier_name.value == "Himalaya Herbs"
    assert not record.needs_review


def test_partial_response_flagged_for_review():
    record = parse(PARTIAL_RESPONSE)
    assert record.expiry_date.value is None
    assert record.quantity.value is None
    assert record.needs_review


def test_overall_confidence_is_mean():
    record = parse(SAMPLE_RESPONSE)
    expected = round((0.85 + 0.90 + 0.88 + 0.95 + 0.92 + 0.80) / 6, 4)
    assert abs(record.overall_confidence - expected) < 0.001
