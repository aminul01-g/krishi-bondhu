"""Traceability service (Phase 2 — Domain depth).

Improvements over the old placeholder:
  * Hash chain links batches (prev_hash -> current_hash) for tamper evidence.
  * The QR encodes a *real, verifiable* URL carrying an HMAC-signed token, so
    scanning it opens a verification page instead of a mock placeholder.
  * `verify_batch_token` allows stateless public verification of a scan.
  * Hash payload excludes volatile timestamps so re-verification is stable.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.production_models import HarvestBatch

try:
    import qrcode
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False

# Base URL a scanned QR should resolve to (a real verify page in production).
_TRACE_BASE = os.getenv("TRACE_VERIFY_BASE", "https://kb.example.org/trace")

# QR image directory — built as an ABSOLUTE path rooted at the project's
# `backend/` dir (not cwd), so QR files are written reliably regardless of
# the process working directory.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))      # .../backend/app/services
_BASE_DIR = os.path.dirname(os.path.dirname(_THIS_DIR))      # .../backend
_QR_DIR = os.path.join(_BASE_DIR, "app", "static", "qrs")

# Whether we are running in DEBUG mode (warn instead of refusing).
_DEBUG = (os.getenv("DEBUG") or "").strip().lower() in ("1", "true", "yes", "on")


def _resolve_secret() -> str:
    """Return the configured trace signing secret, or refuse to sign in production.

    `TRACE_SIGNING_SECRET` MUST be set in production. If it is unset:
      * in DEBUG mode we fall back to an insecure dev default but warn loudly;
      * otherwise we refuse to sign (fail fast) so QR tokens are never forgeable.
    """
    secret = os.getenv("TRACE_SIGNING_SECRET")
    if secret:
        return secret
    if _DEBUG:
        logger = __import__("logging").getLogger("TraceabilityService")
        logger.warning(
            "TRACE_SIGNING_SECRET is not set — using an INSECURE development "
            "default. Scanned QR tokens are forgeable. Set TRACE_SIGNING_SECRET "
            "before deploying."
        )
        return "dev-insecure-trace-secret"
    raise RuntimeError(
        "TRACE_SIGNING_SECRET is not configured. Refusing to sign traceability "
        "tokens with an insecure default. Set TRACE_SIGNING_SECRET to a strong "
        "secret before running outside DEBUG mode."
    )


def _hmac(batch_id: str, current_hash: str) -> str:
    return hmac.new(
        _resolve_secret().encode(), f"{batch_id}:{current_hash}".encode(),
        hashlib.sha256,
    ).hexdigest()


def sign_batch_token(batch_id: str, current_hash: str) -> str:
    """Stateless HMAC token proving a QR belongs to a given batch hash."""
    return _hmac(batch_id, current_hash)


def verify_batch_token(batch_id: str, token: str, current_hash: str) -> bool:
    """Verify a scan token against the batch's recorded hash."""
    expected = _hmac(batch_id, current_hash)
    return hmac.compare_digest(expected, token)


def build_trace_url(batch_id: str, current_hash: str) -> str:
    """A real, verifiable URL encoded into the QR code."""
    return f"{_TRACE_BASE}?batch={batch_id}&h={current_hash}&t={sign_batch_token(batch_id, current_hash)}"


def generate_batch_hash(prev_hash: Optional[str], data: Dict[str, Any]) -> str:
    """
    SHA-256 over the batch's stable fields + previous hash, forming a linked chain.
    Timestamps are excluded so re-verification is deterministic.
    """
    payload = {
        "user_id": data.get("user_id"),
        "crop": data.get("crop"),
        "quantity": data.get("quantity"),
        "inputs": data.get("inputs"),
    }
    sorted_data = sorted(payload.items())
    combined = f"{prev_hash or 'GENESIS'}:{sorted_data}"
    return hashlib.sha256(combined.encode()).hexdigest()


async def register_harvest_batch(
    db: AsyncSession,
    user_id: str,
    crop: str,
    quantity: float,
    inputs_used: List[str],
    unit: str = "kg",
) -> Dict[str, Any]:
    """Registers a harvest batch into the immutable, verifiable ledger."""
    stmt = select(HarvestBatch).order_by(desc(HarvestBatch.created_at)).limit(1)
    last_batch = (await db.execute(stmt)).scalars().first()
    prev_hash = last_batch.current_hash if last_batch else None

    batch_data = {"user_id": user_id, "crop": crop, "quantity": quantity, "inputs": inputs_used}
    current_hash = generate_batch_hash(prev_hash, batch_data)

    batch = HarvestBatch(
        user_id=user_id,
        crop=crop,
        quantity=quantity,
        unit=unit,
        inputs_used=inputs_used,
        prev_hash=prev_hash,
        current_hash=current_hash,
        certification_status="unverified",
    )
    db.add(batch)
    await db.commit()
    await db.refresh(batch)

    # Encode a REAL verifiable URL into the QR (not a placeholder).
    qr_url = None
    if QR_AVAILABLE:
        try:
            img = qrcode.make(build_trace_url(batch.id, current_hash))
            qr_filename = f"qr_{current_hash[:12]}.png"
            qr_path = os.path.join(_QR_DIR, qr_filename)
            os.makedirs(os.path.dirname(qr_path), exist_ok=True)
            img.save(qr_path)
            qr_url = f"/static/qrs/{qr_filename}"
        except Exception as e:
            logger = __import__("logging").getLogger("TraceabilityService")
            logger.warning("QR generation failed", error=str(e))
            qr_url = build_trace_url(batch.id, current_hash)
    else:
        qr_url = build_trace_url(batch.id, current_hash)

    batch.qr_code_url = qr_url
    await db.commit()
    await db.refresh(batch)

    return {
        "batch_id": batch.id,
        "current_hash": batch.current_hash,
        "prev_hash": prev_hash,
        "qr_url": batch.qr_code_url,
        "verify_url": build_trace_url(batch.id, current_hash),
        "trace_token": sign_batch_token(batch.id, current_hash),
    }


async def verify_batch_integrity(db: AsyncSession, batch_id: str) -> Dict[str, Any]:
    """Recomputes the hash chain for a batch to detect tampering."""
    stmt = select(HarvestBatch).where(HarvestBatch.id == batch_id)
    batch = (await db.execute(stmt)).scalars().first()
    if not batch:
        return {"verified": False, "error": "Batch not found"}

    batch_data = {"user_id": batch.user_id, "crop": batch.crop,
                  "quantity": batch.quantity, "inputs": batch.inputs_used}
    recalculated = generate_batch_hash(batch.prev_hash, batch_data)
    if recalculated == batch.current_hash:
        return {"verified": True, "trace_token": sign_batch_token(batch.id, batch.current_hash)}
    return {"verified": False, "error": "Hash mismatch: Data may have been tampered with"}


async def find_premium_buyers(crop: str, quantity: float) -> List[Dict[str, Any]]:
    """Matches harvest to a curated directory of high-value buyers."""
    buyers_directory = [
        {"name": "Dhaka Organic Retail", "crop": "rice", "min_qty": 100, "type": "Retail Chain", "premium": "15%"},
        {"name": "Bengal Export Ltd", "crop": "mango", "min_qty": 500, "type": "Exporter", "premium": "25%"},
        {"name": "Green Agro Processors", "crop": "potato", "min_qty": 200, "type": "Processor", "premium": "10%"},
        {"name": "Pure Farm Co.", "crop": "rice", "min_qty": 50, "type": "Boutique", "premium": "20%"},
    ]
    crop_lower = crop.lower()
    return [b for b in buyers_directory if b["crop"] == crop_lower and quantity >= b["min_qty"]]
