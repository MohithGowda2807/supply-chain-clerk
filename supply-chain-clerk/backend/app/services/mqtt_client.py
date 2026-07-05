"""
MQTT Client Manager

Wraps paho-mqtt in an asyncio-compatible manager.
Handles:
  - Connect / reconnect
  - Publishing bin lighting commands  (warehouse/bin/light)
  - Subscribing to bin confirmation   (warehouse/bin/confirm)
  - Subscribing to device heartbeats  (warehouse/bin/status)

Falls back to USB serial if publish fails within 3 s.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Optional

import paho.mqtt.client as mqtt

from app.services.ws_manager import ws_manager

log = logging.getLogger(__name__)

_BROKER = os.getenv("MQTT_BROKER", "localhost")
_PORT = int(os.getenv("MQTT_PORT", 1883))
_USERNAME = os.getenv("MQTT_USERNAME")
_PASSWORD = os.getenv("MQTT_PASSWORD")

# Topics
TOPIC_LIGHT   = "warehouse/bin/light"
TOPIC_CONFIRM = "warehouse/bin/confirm"
TOPIC_STATUS  = "warehouse/bin/status"


class MQTTManager:
    def __init__(self) -> None:
        self._client: Optional[mqtt.Client] = None
        self._connected = False
        self._last_esp32_seen: Optional[float] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    async def start(self) -> None:
        import uuid
        self._loop = asyncio.get_running_loop()
        client_id = f"supply-chain-clerk-backend-{uuid.uuid4().hex[:8]}"
        self._client = mqtt.Client(client_id=client_id)
        
        if _USERNAME and _PASSWORD:
            self._client.username_pw_set(_USERNAME, _PASSWORD)
        
        if _PORT == 8883:
            self._client.tls_set()

        self._client.on_connect    = self._on_connect
        self._client.on_message    = self._on_message
        self._client.on_disconnect = self._on_disconnect

        try:
            self._client.connect(_BROKER, _PORT, keepalive=60)
            self._client.loop_start()
            log.info("MQTT connected to %s:%s", _BROKER, _PORT)
        except Exception as exc:
            log.warning("MQTT connection failed: %s — running without MQTT", exc)

    async def stop(self) -> None:
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            log.info("MQTT disconnected.")

    # ── Callbacks ─────────────────────────────────────────────────────────────
    def _on_connect(self, client, userdata, flags, rc):
        self._connected = rc == 0
        if self._connected:
            client.subscribe(TOPIC_CONFIRM)
            client.subscribe(TOPIC_STATUS)
            log.info("MQTT subscribed to %s, %s", TOPIC_CONFIRM, TOPIC_STATUS)

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        log.warning("MQTT disconnected (rc=%s)", rc)

    def _on_message(self, client, userdata, msg: mqtt.MQTTMessage):
        """Dispatch incoming MQTT messages to WebSocket clients."""
        try:
            payload = json.loads(msg.payload.decode())
        except json.JSONDecodeError:
            return

        topic = msg.topic
        if topic == TOPIC_CONFIRM:
            event = {"event_type": "BIN_CONFIRMED", **payload}
        elif topic == TOPIC_STATUS:
            self._last_esp32_seen = time.time()
            event = {"event_type": "SYSTEM_STATUS", **payload}
        else:
            return

        if getattr(self, "_loop", None) and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                ws_manager.broadcast(event),
                self._loop,
            )

    # ── Publishing ────────────────────────────────────────────────────────────
    async def publish_bin_light(
        self, bin_code: str, colour: str = "green", led_index: int = 0
    ) -> bool:
        """
        Publish a bin lighting command.
        Returns True on success, False on MQTT failure (triggers serial fallback).
        """
        if not self._connected or self._client is None:
            return False

        payload = json.dumps({
            "bin_id":    bin_code,
            "color":     colour,
            "led_index": led_index,
            "ts":        int(time.time()),
        })
        result = self._client.publish(TOPIC_LIGHT, payload, qos=1)

        # Wait up to 3 s for PUBACK
        deadline = asyncio.get_event_loop().time() + 3.0
        while not result.is_published():
            if asyncio.get_event_loop().time() > deadline:
                log.warning("MQTT publish timeout for bin %s", bin_code)
                return False
            await asyncio.sleep(0.05)

        log.info("MQTT published bin light: %s → %s", bin_code, colour)
        return True

    # ── Status ────────────────────────────────────────────────────────────────
    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def last_esp32_seen(self) -> Optional[float]:
        return self._last_esp32_seen


mqtt_manager = MQTTManager()
