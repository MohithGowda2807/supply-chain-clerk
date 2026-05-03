"""
WebSocket Connection Manager

Tracks all active React dashboard WebSocket clients and broadcasts
typed JSON events to all of them.

Event types:
  INTAKE_CREATED   — new document processed
  BIN_CONFIRMED    — ESP32 confirmed product placed
  EXPIRY_ALERT     — batch near expiry
  SYSTEM_STATUS    — ESP32 heartbeat / latency metrics
"""
from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import WebSocket

log = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._active: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._active.append(ws)
        log.info("WebSocket client connected. Total: %d", len(self._active))

    def disconnect(self, ws: WebSocket) -> None:
        self._active = [c for c in self._active if c is not ws]
        log.info("WebSocket client disconnected. Total: %d", len(self._active))

    async def broadcast(self, event: dict[str, Any]) -> None:
        """Send a JSON event to every connected client."""
        dead: list[WebSocket] = []
        for ws in self._active:
            try:
                await ws.send_text(json.dumps(event))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


ws_manager = ConnectionManager()
