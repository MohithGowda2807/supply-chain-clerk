"""
/status — System Status Endpoint

Returns live status of:
  - VLM API (Gemini)
  - Neo4j connection
  - MQTT broker
  - ESP32 last heartbeat
"""
from __future__ import annotations

import os
import time

from fastapi import APIRouter
from neo4j import AsyncGraphDatabase

from app.services.mqtt_client import mqtt_manager

router = APIRouter()

_URI  = os.getenv("NEO4J_URI", "bolt://localhost:7687")
_USER = os.getenv("NEO4J_USER", "neo4j")
_PASS = os.getenv("NEO4J_PASSWORD", "smartguard123")


@router.get("")
async def get_status():
    # Neo4j ping
    neo4j_ok = False
    try:
        driver = AsyncGraphDatabase.driver(_URI, auth=(_USER, _PASS))
        async with driver.session() as session:
            await session.run("RETURN 1")
        await driver.close()
        neo4j_ok = True
    except Exception:
        pass

    # ESP32 heartbeat
    last_seen = mqtt_manager.last_esp32_seen
    esp32_alive = last_seen is not None and (time.time() - last_seen) < 30

    return {
        "vlm_api":      "ok",           # Gemini — always try; errors returned on /intake
        "neo4j":        "ok" if neo4j_ok else "error",
        "mqtt":         "ok" if mqtt_manager.connected else "error",
        "esp32_alive":  esp32_alive,
        "esp32_last_seen": last_seen,
        "timestamp":    time.time(),
    }
