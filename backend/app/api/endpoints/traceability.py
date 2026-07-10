from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db import get_db
from app.models.db_models import User
from app.models.production_models import HarvestBatch
from app.services.traceability_service import (
    register_harvest_batch,
    verify_batch_integrity,
    verify_batch_token,
)

router = APIRouter()


class RegisterBatchRequest(BaseModel):
    crop: str = Field(..., description="Name of the harvested crop")
    quantity: float = Field(..., gt=0, description="Amount harvested")
    unit: str = Field("kg", description="Unit of measure")
    inputs_used: list[str] | None = Field(None, description="Inputs and materials used in production")


@router.post("/batch")
@router.post("/batches")
async def register_batch(
    payload: RegisterBatchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Registers a harvest batch into the immutable, verifiable ledger.
    Delegates to the async `register_harvest_batch` service, which maintains the
    hash chain, generates the QR/verify URL, and signs a public token.
    """
    try:
        user_id = current_user.external_id
        result = await register_harvest_batch(
            db,
            user_id,
            payload.crop,
            payload.quantity,
            payload.inputs_used or [],
            unit=payload.unit,
        )
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to register batch: {e}")


@router.get("/integrity/{batch_id}")
async def batch_integrity(
    batch_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Verifies the hash-chain integrity of a batch to detect tampering.
    Async service method — must be awaited.
    """
    try:
        result = await verify_batch_integrity(db, batch_id)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to verify integrity: {e}")


@router.get("/verify")
async def public_verify(
    batch: str = Query(..., description="Batch id from the scanned QR"),
    h: str = Query(..., description="Recorded current hash of the batch"),
    t: str = Query(..., description="HMAC scan token from the scanned QR"),
):
    """
    Public, unauthenticated consumer-facing verification of a scanned batch token.
    `verify_batch_token` is synchronous — do NOT await it.
    """
    valid = verify_batch_token(batch, t, h)
    return {"valid": bool(valid), "batch": batch}


@router.get("/batches/{batch_id}")
async def get_harvest_batch(
    batch_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve a harvest batch by ID (read-only)."""
    result = await db.execute(select(HarvestBatch).where(HarvestBatch.id == batch_id))
    batch = result.scalars().first()
    if not batch or batch.user_id != current_user.external_id:
        raise HTTPException(status_code=404, detail="Harvest batch not found")

    return {
        "id": batch.id,
        "user_id": batch.user_id,
        "crop": batch.crop,
        "quantity": batch.quantity,
        "unit": batch.unit,
        "prev_hash": batch.prev_hash,
        "current_hash": batch.current_hash,
        "inputs_used": batch.inputs_used,
        "harvest_date": batch.harvest_date,
        "certification_status": batch.certification_status,
        "qr_code_url": batch.qr_code_url,
        "created_at": batch.created_at,
    }

