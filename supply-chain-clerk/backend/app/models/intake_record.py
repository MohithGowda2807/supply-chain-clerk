"""
Pydantic schema for a supply-chain intake record.

Every extracted field carries a per-field confidence score (0.0–1.0).
Records with overall_confidence < 0.75 are flagged as NEEDS_REVIEW.
"""
from __future__ import annotations

from datetime import date
from statistics import mean
from typing import Optional

from pydantic import BaseModel, field_validator


class FieldWithConfidence(BaseModel):
    """Generic wrapper that pairs an extracted value with its confidence."""

    value: Optional[str | int | date] = None
    confidence: float  # 0.0 (illegible/absent) … 1.0 (certain)

    @field_validator("confidence")
    @classmethod
    def clamp_confidence(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


class IntakeRecord(BaseModel):
    """
    Full structured representation of one intake document.

    Fields
    ------
    batch_no        : Supplier batch / lot number.
    expiry_date     : Expiry date in YYYY-MM-DD format.
    quantity        : Integer quantity of units.
    supplier_name   : Name of the supplying company.
    product_name    : Common name of the product.
    unit_of_measure : Unit (units / strips / bottles / kg …).
    """

    batch_no: FieldWithConfidence
    expiry_date: FieldWithConfidence
    quantity: FieldWithConfidence
    supplier_name: FieldWithConfidence
    product_name: FieldWithConfidence
    unit_of_measure: FieldWithConfidence

    @property
    def overall_confidence(self) -> float:
        scores = [
            f.confidence
            for f in [
                self.batch_no,
                self.expiry_date,
                self.quantity,
                self.supplier_name,
                self.product_name,
                self.unit_of_measure,
            ]
        ]
        return round(mean(scores), 4)

    @property
    def needs_review(self) -> bool:
        return self.overall_confidence < 0.75


class IntakeResponse(BaseModel):
    """Response returned from the /intake/capture endpoint."""

    record: IntakeRecord
    assigned_bin: Optional[str]
    overall_confidence: float
    review_required: bool
    intake_id: str  # Neo4j Batch node internal ID
    latency_ms: float
