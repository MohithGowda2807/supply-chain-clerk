"""
USB Serial Fallback

If MQTT publish fails, the backend attempts to send the same bin-light
command over USB serial to the ESP32 at 115200 baud.

Activates within 3 s of MQTT failure (matching Step 5.2 of the roadmap).
"""
from __future__ import annotations

import json
import logging
import os
import time

log = logging.getLogger(__name__)

_SERIAL_PORT = os.getenv("SERIAL_PORT", "COM3")   # override via .env
_BAUD        = 115200


def send_bin_command_serial(bin_code: str, colour: str, led_index: int) -> bool:
    """
    Send a bin lighting command over USB serial.
    Returns True on success, False if pyserial unavailable or port fails.
    """
    try:
        import serial  # type: ignore
    except ImportError:
        log.warning("pyserial not installed — serial fallback unavailable.")
        return False

    payload = json.dumps({
        "bin_id":    bin_code,
        "colour":    colour,
        "led_index": led_index,
        "ts":        int(time.time()),
    }) + "\n"

    try:
        with serial.Serial(_SERIAL_PORT, _BAUD, timeout=2) as ser:
            ser.write(payload.encode())
            log.info("Serial fallback sent to %s: %s", _SERIAL_PORT, payload.strip())
            return True
    except Exception as exc:
        log.error("Serial fallback failed: %s", exc)
        return False
