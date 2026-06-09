"""
VLM Service Client — Google Gemini 2.0 Flash (google-genai SDK)

Sends an invoice / packing-slip image to Gemini and returns a parsed
dict matching the IntakeRecord schema.
"""
from __future__ import annotations

import asyncio
import base64
import io
import json
import os
import re
from pathlib import Path

from google import genai
from google.genai import types
from PIL import Image

# ── Configuration ─────────────────────────────────────────────────────────────
_KEYS_ENV = os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY") or ""
_API_KEYS = [k.strip() for k in _KEYS_ENV.split(",") if k.strip()]

if not _API_KEYS:
    _API_KEYS = ["dummy_key"]  # Prevent startup crash if env is missing

_CLIENTS = [genai.Client(api_key=key) for key in _API_KEYS]
_CURRENT_CLIENT_INDEX = 0

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "v1_extraction.txt"
PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")

_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
_CURRENT_MODEL_INDEX = 0


# ── Image pre-processing ──────────────────────────────────────────────────────
def preprocess_image(image_bytes: bytes) -> bytes:
    """
    Normalise to JPEG RGB at ≤ 4 MP for consistent quality and lower cost.
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    max_pixels = 4_000_000
    if img.width * img.height > max_pixels:
        scale = (max_pixels / (img.width * img.height)) ** 0.5
        img = img.resize(
            (int(img.width * scale), int(img.height * scale)),
            Image.LANCZOS,
        )

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


# ── Extraction ────────────────────────────────────────────────────────────────
async def extract_from_document(image_bytes: bytes) -> dict:
    """
    Send *image_bytes* to Gemini and return the raw parsed JSON dict.
    Automatically rotates through available API keys and models on 503 or 429 errors.
    """
    global _CURRENT_CLIENT_INDEX, _CURRENT_MODEL_INDEX

    processed = preprocess_image(image_bytes)
    b64_data = base64.b64encode(processed).decode()

    max_retries = max(len(_CLIENTS) * len(_MODELS), 5)
    last_exc = None

    for attempt in range(max_retries):
        client = _CLIENTS[_CURRENT_CLIENT_INDEX]
        model = _MODELS[_CURRENT_MODEL_INDEX]
        try:
            response = await client.aio.models.generate_content(
                model=model,
                contents=[
                    types.Part.from_text(text=PROMPT),
                    types.Part.from_bytes(
                        data=base64.b64decode(b64_data),
                        mime_type="image/jpeg",
                    ),
                ],
                config=types.GenerateContentConfig(temperature=0.0),
            )

            text = response.text.strip()
            # Strip optional ``` fences the model occasionally wraps around JSON
            text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()

            try:
                return json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Gemini returned non-JSON response:\n{text}"
                ) from exc

        except Exception as exc:
            exc_str = str(exc)
            if any(err in exc_str for err in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "Too Many Requests")):
                # If it's a 503 High Demand, the model is overloaded, switch models
                if "503" in exc_str or "UNAVAILABLE" in exc_str:
                    _CURRENT_MODEL_INDEX = (_CURRENT_MODEL_INDEX + 1) % len(_MODELS)
                
                # If it's a 429 Rate Limit, our key is exhausted, switch keys
                if "429" in exc_str or "RESOURCE_EXHAUSTED" in exc_str or "Too Many Requests" in exc_str:
                    _CURRENT_CLIENT_INDEX = (_CURRENT_CLIENT_INDEX + 1) % len(_CLIENTS)
                
                last_exc = exc
                await asyncio.sleep(2.0)
                continue
            else:
                raise exc

    raise RuntimeError(f"All Gemini API requests failed after {max_retries} attempts. Last error: {last_exc}") from last_exc
