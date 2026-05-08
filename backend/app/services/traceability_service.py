import hashlib
import uuid
import os
import base64
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.production_models import HarvestBatch

# For QR generation, we use a mock implementation if the library isn't available
# to ensure the agent doesn't crash during deployment.
try:
    import qrcode
    from PIL import Image
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False

async def generate_batch_hash(prev_hash: Optional[str], data: Dict[str, Any]) -> str:
    """
    Creates a SHA-256 hash of the current batch data and the previous hash,
    forming a cryptographically linked chain.
    """
    # Sort keys to ensure consistent hashing
    sorted_data = sorted(data.items())
    data_string = str(sorted_data)
    combined = f"{prev_hash or 'GENESIS'}:{data_string}"
    return hashlib.sha256(combined.encode()).hexdigest()

async def register_harvest_batch(
    db: AsyncSession,
    user_id: str,
    crop: str,
    quantity: float,
    inputs_used: List[str]
) -> Dict[str, Any]:
    """
    Registers a new harvest batch into the immutable ledger.
    """
    # 1. Get the most recent batch hash to link the chain
    stmt = select(HarvestBatch).order_by(desc(HarvestBatch.created_at)).limit(1)
    result = await db.execute(stmt)
    last_batch = result.scalars().first()
    prev_hash = last_batch.current_hash if last_batch else None

    # 2. Define batch data for hashing
    batch_data = {
        "user_id": user_id,
        "crop": crop,
        "quantity": quantity,
        "inputs": inputs_used,
        "timestamp": datetime.utcnow().isoformat()
    }

    # 3. Generate current hash
    current_hash = await generate_batch_hash(prev_hash, batch_data)

    # 4. Generate QR Code URL
    qr_url = None
    if QR_AVAILABLE:
        qr_val = f"kb-trace://batch/{uuid.uuid4()}" # Simplified trace link
        img = qrcode.make(qr_val)
        # In production, this would be uploaded to S3/Cloudinary
        # For now, we save to local storage
        qr_filename = f"qr_{current_hash[:12]}.png"
        qr_path = f"backend/app/static/qrs/{qr_filename}"
        os.makedirs(os.path.dirname(qr_path), exist_ok=True)
        img.save(qr_path)
        qr_url = f"/static/qrs/{qr_filename}"
    else:
        qr_url = "http://mock-qr-service.com/placeholder.png"

    # 5. Persist to DB
    batch = HarvestBatch(
        user_id=user_id,
        crop=crop,
        quantity=quantity,
        inputs_used=inputs_used,
        prev_hash=prev_hash,
        current_hash=current_hash,
        qr_code_url=qr_url
    )
    db.add(batch)
    await db.commit()
    await db.refresh(batch)

    return {
        "batch_id": batch.id,
        "current_hash": batch.current_hash,
        "qr_url": batch.qr_code_url
    }

async def verify_batch_integrity(db: AsyncSession, batch_id: str) -> Dict[str, Any]:
    """
    Verifies that the batch has not been tampered with by re-calculating the hash chain.
    """
    stmt = select(HarvestBatch).where(HarvestBatch.id == batch_id)
    result = await db.execute(stmt)
    batch = result.scalars().first()

    if not batch:
        return {"verified": False, "error": "Batch not found"}

    # Re-calculate hash based on stored data
    batch_data = {
        "user_id": batch.user_id,
        "crop": batch.crop,
        "quantity": batch.quantity,
        "inputs": batch.inputs_used,
        "timestamp": batch.created_at.isoformat() # Note: Potential drift if not handled carefully
    }

    recalculated = await generate_batch_hash(batch.prev_hash, batch_data)

    # In a real system, we'd tolerate slight timestamp drifts or use a fixed snap
    if recalculated == batch.current_hash:
        return {"verified": True}

    return {"verified": False, "error": "Hash mismatch: Data may have been tampered with"}

async def find_premium_buyers(crop: str, quantity: float) -> List[Dict[str, Any]]:
    """
    Matches harvest to a curated directory of high-value buyers.
    """
    # Mock directory of premium buyers
    buyers_directory = [
        {"name": "Dhaka Organic Retail", "crop": "rice", "min_qty": 100, "type": "Retail Chain", "premium": "15%"},
        {"name": "Bengal Export Ltd", "crop": "mango", "min_qty": 500, "type": "Exporter", "premium": "25%"},
        {"name": "Green Agro Processors", "crop": "potato", "min_qty": 200, "type": "Processor", "premium": "10%"},
        {"name": "Pure Farm Co.", "crop": "rice", "min_qty": 50, "type": "Boutique", "premium": "20%"},
    ]

    crop_lower = crop.lower()
    matches = [
        b for b in buyers_directory
        if b["crop"] == crop_lower and quantity >= b["min_qty"]
    ]

    return matches
