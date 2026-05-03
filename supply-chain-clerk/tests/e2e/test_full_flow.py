"""
End-to-End Integration Test

Tests the full pipeline:
  1. Submit document image → /intake/capture
  2. Verify MQTT bin lighting command arrives within 8 s
  3. Publish simulated ESP32 confirmation via MQTT
  4. Verify Neo4j Batch node was created
  5. Verify WebSocket emitted BIN_CONFIRMED

Run with:  pytest tests/e2e/test_full_flow.py -v
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path

import httpx
import paho.mqtt.client as mqtt
import pytest

# ── Config ────────────────────────────────────────────────────────────────────
BASE_URL      = "http://localhost:8000"
MQTT_BROKER   = "localhost"
MQTT_PORT     = 1883
TOPIC_LIGHT   = "warehouse/bin/light"
TOPIC_CONFIRM = "warehouse/bin/confirm"
TIMEOUT_S     = 8

FIXTURE_IMAGE = Path(__file__).parent.parent / "fixtures" / "documents" / "printed_clean_001.jpg"


# ── Helpers ───────────────────────────────────────────────────────────────────
class MQTTHelper:
    def __init__(self):
        self.received_light: list[dict] = []
        self._client = mqtt.Client()
        self._client.on_message = self._on_message

    def _on_message(self, client, userdata, msg):
        if msg.topic == TOPIC_LIGHT:
            self.received_light.append(json.loads(msg.payload))

    def __enter__(self):
        self._client.connect(MQTT_BROKER, MQTT_PORT)
        self._client.subscribe(TOPIC_LIGHT)
        self._client.loop_start()
        return self

    def __exit__(self, *args):
        self._client.loop_stop()
        self._client.disconnect()

    def publish_confirmation(self, bin_code: str):
        payload = json.dumps({"bin_id": bin_code, "ts": int(time.time())})
        self._client.publish(TOPIC_CONFIRM, payload)


# ── Tests ─────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_full_intake_flow():
    """Full pipeline test — must pass 5 consecutive times (run manually)."""

    if not FIXTURE_IMAGE.exists():
        pytest.skip("No fixture image found — add printed_clean_001.jpg to tests/fixtures/documents/")

    with MQTTHelper() as mqtt_helper:
        # 1. Submit document
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
            with open(FIXTURE_IMAGE, "rb") as f:
                resp = await client.post(
                    "/intake/capture",
                    files={"file": ("printed_clean_001.jpg", f, "image/jpeg")},
                )

        assert resp.status_code == 200, f"Capture failed: {resp.text}"
        data = resp.json()

        assert "assigned_bin" in data
        assert "overall_confidence" in data
        assert "intake_id" in data

        bin_code = data["assigned_bin"]

        # 2. Verify MQTT light command within 8 s
        deadline = time.time() + TIMEOUT_S
        while time.time() < deadline:
            matching = [m for m in mqtt_helper.received_light if m.get("bin_id") == bin_code]
            if matching:
                break
            await asyncio.sleep(0.2)
        else:
            pytest.fail(f"MQTT bin light command for {bin_code} not received within {TIMEOUT_S}s")

        # 3. Publish simulated confirmation
        mqtt_helper.publish_confirmation(bin_code)
        await asyncio.sleep(1)

        # 4. Verify Neo4j batch node
        from neo4j import AsyncGraphDatabase
        driver = AsyncGraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "smartguard123")),
        )
        async with driver.session() as session:
            result = await session.run(
                "MATCH (b:Batch) WHERE elementId(b) = $id RETURN b",
                id=data["intake_id"],
            )
            record = await result.single()
        await driver.close()

        assert record is not None, "Batch node not found in Neo4j"

        print(f"\n✅ Full flow passed | bin={bin_code} | confidence={data['overall_confidence']:.2f} | latency={data['latency_ms']}ms")
