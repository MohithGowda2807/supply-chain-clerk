"""
VLM Service Client — Google Gemini 2.0 Flash (google-genai SDK)

Sends an invoice / packing-slip image to Gemini and returns a parsed
dict matching the IntakeRecord schema.
"""
from __future__ import annotations

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
_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=_API_KEY)

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "v1_extraction.txt"
PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")

_MODEL = "gemini-2.0-flash"


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

    Raises
    ------
    ValueError
        If the model response cannot be parsed as valid JSON.
    """
    processed = preprocess_image(image_bytes)
    b64_data = base64.b64encode(processed).decode()

    response = client.models.generate_content(
        model=_MODEL,
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
