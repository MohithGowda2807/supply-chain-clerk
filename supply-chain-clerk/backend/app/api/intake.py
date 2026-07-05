"""
/intake/capture — Primary Intake Endpoint

POST /intake/capture
  - Accepts: multipart/form-data  (file: UploadFile, operator_id: str?)
  - Calls VLM → validates → assigns bin → writes Neo4j → publishes MQTT
  - Returns: IntakeResponse JSON
"""
from __future__ import annotations

import asyncio
import time
import uuid
import logging
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.models.intake_record import IntakeRecord, IntakeResponse
from app.services import local_ai_client, bin_assigner
from app.services.mqtt_client import mqtt_manager
from app.services.serial_fallback import send_bin_command_serial
from app.services.ws_manager import ws_manager

log = logging.getLogger(__name__)
router = APIRouter()


@router.post("/capture", response_model=IntakeResponse)
async def capture_intake(
    file: UploadFile = File(..., description="Document image (JPEG/PNG/PDF scan)"),
    operator_id: Optional[str] = Form(None),
):
    t_start = time.perf_counter()

    try:
        # ── 1. Local AI Extraction (OCR + NER) ───────────────────────────────────
        image_bytes = await file.read()
        try:
            raw = await local_ai_client.extract_from_document(image_bytes)
        except ValueError as exc:
            # FALLBACK: Tell ESP32 to route to Bin 2 (Error) so it doesn't hang forever
            await mqtt_manager.publish_bin_light(bin_code="A02", colour="red", led_index=0)
            raise HTTPException(status_code=422, detail=str(exc))

        # ── 2. Pydantic Validation ────────────────────────────────────────────────
        record = IntakeRecord(**raw)

        # ── 3. Bin Assignment (async, pure Cypher) ────────────────────────────────
        product_name = record.product_name.value or "Unknown"
        category = local_ai_client.classify_product(product_name)
        assigned_bin = await bin_assigner.assign_bin(category, product_name)

        if assigned_bin is None:
            log.warning("No bin available in zone '%s' for '%s'", category, product_name)
            assigned_bin = "OVERFLOW"

        # ── 4. Write Neo4j + Publish MQTT (concurrent) ────────────────────────────
        batch_no   = record.batch_no.value or f"AUTO-{uuid.uuid4().hex[:8].upper()}"
        expiry_str = str(record.expiry_date.value) if record.expiry_date.value else None
        qty        = record.quantity.value if isinstance(record.quantity.value, int) else None
        uom        = record.unit_of_measure.value or "units"

        intake_id, mqtt_ok = await asyncio.gather(
            bin_assigner.write_intake_event(
                batch_no      = batch_no,
                product_name  = product_name,
                supplier_name = record.supplier_name.value or "Unknown",
                expiry_date   = expiry_str,
                quantity      = qty,
                unit_of_measure = uom,
                bin_code      = assigned_bin,
                confidence    = record.overall_confidence,
            ),
            mqtt_manager.publish_bin_light(
                bin_code  = assigned_bin,
                colour    = "amber" if record.needs_review else "green",
                led_index = 0,   # resolved from Neo4j in production
            ),
        )

        # ── 5. Serial fallback if MQTT failed or ESP32 is offline ────────────────
        esp32_online = mqtt_manager.last_esp32_seen is not None and (time.time() - mqtt_manager.last_esp32_seen) < 30
        if not mqtt_ok or not esp32_online:
            log.info("MQTT or device offline — attempting serial fallback for bin %s", assigned_bin)
            send_bin_command_serial(
                bin_code  = assigned_bin,
                colour    = "amber" if record.needs_review else "green",
                led_index = 0,
            )

        # ── 6. WebSocket broadcast ────────────────────────────────────────────────
        latency_ms = round((time.perf_counter() - t_start) * 1000, 1)
        event = {
            "event_type":   "INTAKE_CREATED",
            "intake_id":    intake_id,
            "batch_no":     batch_no,
            "product_name": product_name,
            "assigned_bin": assigned_bin,
            "confidence":   record.overall_confidence,
            "review_required": record.needs_review,
            "latency_ms":   latency_ms,
            "operator_id":  operator_id,
        }
        await ws_manager.broadcast(event)

        return IntakeResponse(
            record           = record,
            assigned_bin     = assigned_bin,
            overall_confidence = record.overall_confidence,
            review_required  = record.needs_review,
            intake_id        = intake_id,
            latency_ms       = latency_ms,
        )
    except HTTPException:
        raise
    except Exception as exc:
        log.error("Capture intake failed: %s", exc, exc_info=True)
        # FALLBACK: Tell ESP32 to route to Bin 2 (Error) so it doesn't hang forever
        asyncio.create_task(mqtt_manager.publish_bin_light(bin_code="A02", colour="red", led_index=0))
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {exc}")

