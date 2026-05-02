"""OCR service wrapper for product label scanning."""

import os
import io
import base64
from typing import Dict

TESSERACT_CMD = os.getenv("TESSERACT_CMD", "/usr/bin/tesseract")
TESSERACT_LANGUAGES = os.getenv("TESSERACT_LANGUAGES", "eng+ben")


def _load_tesseract():
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter

    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    return pytesseract, Image, ImageEnhance, ImageFilter


def preprocess_image(image):
    _, Image, ImageEnhance, ImageFilter = _load_tesseract()
    image = image.convert("RGB")
    image = image.resize((int(image.width * 1.5), int(image.height * 1.5)), Image.LANCZOS)
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.5)
    image = image.filter(ImageFilter.SHARPEN)
    return image


def extract_text_from_base64(image_base64: str) -> str:
    pytesseract, Image, _, _ = _load_tesseract()
    image_bytes = base64.b64decode(image_base64)
    image = Image.open(io.BytesIO(image_bytes))
    image = preprocess_image(image)
    text = pytesseract.image_to_string(image, lang=TESSERACT_LANGUAGES)
    return text


def parse_label_text(text: str) -> Dict[str, str]:
    # Basic label parsing with keyword extraction
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    parsed = {"raw_text": text, "product_name": None, "active_ingredient": None, "npk_ratio": None, "expiry": None, "dose": None}
    for line in lines:
        lower = line.lower()
        if "npk" in lower or "n-p-k" in lower or "ratio" in lower:
            parsed["npk_ratio"] = line
        if "expiry" in lower or "মেয়াদ" in lower or "মেয়াদোত্তীর্ণ" in lower:
            parsed["expiry"] = line
        if "active ingredient" in lower or "active" in lower or "উপাদান" in lower:
            parsed["active_ingredient"] = line
        if "dose" in lower or "ডোজ" in lower or "প্রয়োগ" in lower:
            parsed["dose"] = line
        if parsed["product_name"] is None and len(line) > 5 and not any(keyword in lower for keyword in ["npk", "expiry", "date", "বৈধ", "উপাদান"]):
            parsed["product_name"] = line
    return parsed
