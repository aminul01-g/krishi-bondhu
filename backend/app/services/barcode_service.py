"""Barcode and QR code scanning utilities."""

import io
import base64
from typing import Optional


def decode_barcode_base64(image_base64: str) -> Optional[str]:
    from PIL import Image
    from pyzbar.pyzbar import decode

    image_data = base64.b64decode(image_base64)
    image = Image.open(io.BytesIO(image_data)).convert("RGB")
    decoded = decode(image)
    if not decoded:
        return None
    return decoded[0].data.decode("utf-8")
