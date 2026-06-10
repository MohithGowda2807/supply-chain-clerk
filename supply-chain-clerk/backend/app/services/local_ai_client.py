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

_READER = None
_NLP = None
_CLASSIFIER = None

def get_reader():
    global _READER
    if _READER is None:
        import easyocr
        log.info("Downloading and loading EasyOCR model for the first time...")
        _READER = easyocr.Reader(['en'], gpu=False) # CPU inference
    return _READER

def get_nlp():
    global _NLP
    if _NLP is None:
        import spacy
        model_path = Path(__file__).parent.parent.parent / "invoice_ner_model"
        if model_path.exists():
            log.info("Loading Custom NLP model successfully.")
            _NLP = spacy.load(str(model_path))
        else:
            log.error("Custom NLP model not found at %s", model_path)
    return _NLP

def get_classifier():
    global _CLASSIFIER
    if _CLASSIFIER is None:
        import joblib
        model_path = Path(__file__).parent.parent.parent / "product_classifier.joblib"
        if model_path.exists():
            log.info("Loading Scikit-Learn Product Classifier...")
            _CLASSIFIER = joblib.load(model_path)
        else:
            log.error("Product classifier not found at %s", model_path)
    return _CLASSIFIER

def classify_product(product_name: str) -> str:
    """Uses ML to categorize a product name into herbal, analgesic, or supplement."""
    classifier = get_classifier()
    if classifier is None:
        return "herbal" # Fallback if model missing
    
    # Predict returns an array, we grab the first item
    prediction = classifier.predict([product_name])[0]
    return prediction

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
    def _process():
        nlp = get_nlp()
        if nlp is None:
            raise ValueError("Custom NLP model is missing. Cannot process document.")
            
        reader = get_reader()
        img_array = preprocess_image(image_bytes)
        # 1. OCR
        results = reader.readtext(img_array, detail=0, paragraph=True)
        raw_text = "\n".join(results)
        log.info(f"OCR Extracted Text:\n{raw_text}")
        
        # 2. NLP Extraction
        doc = nlp(raw_text)
        
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

    loop = asyncio.get_running_loop()
    output = await loop.run_in_executor(None, _process)
    return output
