"""
Unit tests for the IntakeRecord Pydantic schema.
Run: pytest tests/test_schema.py -v
"""
from app.models.intake_record import IntakeRecord, FieldWithConfidence


def make_record(**overrides):
    defaults = dict(
        batch_no={"value": "BT-2024-001", "confidence": 0.95},
        expiry_date={"value": "2026-12-31", "confidence": 0.90},
        quantity={"value": 100, "confidence": 0.88},
        supplier_name={"value": "Himalaya Herbs", "confidence": 0.95},
        product_name={"value": "Ashwagandha Extract", "confidence": 0.92},
        unit_of_measure={"value": "units", "confidence": 0.99},
    )
    defaults.update(overrides)
    return IntakeRecord(**defaults)


def test_overall_confidence_high():
    record = make_record()
    assert record.overall_confidence >= 0.90
    assert not record.needs_review


def test_needs_review_when_low_confidence():
    record = make_record(
        batch_no={"value": None, "confidence": 0.0},
        expiry_date={"value": None, "confidence": 0.0},
        quantity={"value": None, "confidence": 0.0},
    )
    assert record.overall_confidence < 0.75
    assert record.needs_review


def test_confidence_clamped():
    field = FieldWithConfidence(value="test", confidence=1.5)
    assert field.confidence == 1.0
    field2 = FieldWithConfidence(value="test", confidence=-0.5)
    assert field2.confidence == 0.0


def test_missing_fields_produce_null():
    record = make_record(
        supplier_name={"value": None, "confidence": 0.0},
        product_name={"value": None, "confidence": 0.0},
    )
    assert record.supplier_name.value is None
    assert record.product_name.value is None
