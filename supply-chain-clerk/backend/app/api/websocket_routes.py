"""
WebSocket Route — /ws

All React dashboard instances connect here.
The server pushes typed JSON events:
  INTAKE_CREATED, BIN_CONFIRMED, EXPIRY_ALERT, SYSTEM_STATUS
"""
from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.ws_manager import ws_manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive; client pings every 30 s
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
