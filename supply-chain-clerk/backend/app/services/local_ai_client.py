import io
import json
import logging
import re
from pathlib import Path
import numpy as np
from PIL import Image
import asyncio

import easyocr
import spacy

log = logging.getLogger(__name__)

# Initialize ML models once at startup
log.info("Loading Custom Local AI models...")
_READER = easyocr.Reader(['en'], gpu=False) # CPU inference

_MODEL_PATH = Path(__file__).parent.parent.parent / "invoice_ner_model"
if _MODEL_PATH.exists():
    _NLP = spacy.load(str(_MODEL_PATH))
    log.info("Custom NLP model loaded successfully.")
else:
    log.error("Custom NLP model not found at %s. Please run train_ner.py", _MODEL_PATH)
    _NLP = None

def preprocess_image(image_bytes: bytes) -> np.ndarray:
    """Convert bytes to a numpy array suitable for EasyOCR"""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    # Resize to max 1500 pixels wide for speed
    max_w = 1500
    if img.width > max_w:
        scale = max_w / img.width
        img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
    return np.array(img)

async def extract_from_document(image_bytes: bytes) -> dict:
    """
    Local AI Pipeline:
    1. OCR via EasyOCR
    2. NER via Custom SpaCy Model
    """
    if _NLP is None:
        raise ValueError("Custom NLP model is missing. Cannot process document.")
        
    log.info("Starting local OCR processing...")
    # Offload image processing and OCR to a separate thread since it's blocking
    loop = asyncio.get_running_loop()
    
    def _process():
        img_array = preprocess_image(image_bytes)
        # 1. OCR
        results = _READER.readtext(img_array, detail=0, paragraph=True)
        raw_text = "\n".join(results)
        log.info(f"OCR Extracted Text:\n{raw_text}")
        
        # 2. NLP Extraction
        doc = _NLP(raw_text)
        
        output = {
            "batch_no":        {"value": None, "confidence": 0.0},
            "expiry_date":     {"value": None, "confidence": 0.0},
            "quantity":        {"value": None, "confidence": 0.0},
            "supplier_name":   {"value": None, "confidence": 0.0},
            "product_name":    {"value": None, "confidence": 0.0},
            "unit_of_measure": {"value": None, "confidence": 0.0}
        }
        
        for ent in doc.ents:
            label = ent.label_
            if label in output:
                val = ent.text.strip()
                
                # Clean up specific fields based on common OCR errors
                if label == "quantity":
                    val = re.sub(r"[^\d]", "", val)
                    try:
                        val = int(val)
                    except:
                        val = None
                        
                if val is not None:
                    output[label] = {"value": val, "confidence": 0.95} # Custom trained model confidence
        return output

    output = await loop.run_in_executor(None, _process)
    return output
