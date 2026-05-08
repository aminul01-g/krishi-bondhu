from datetime import datetime
import hashlib
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db import get_db
from app.models.production_models import HarvestBatch
from app.models.db_models import User

router = APIRouter()

class TraceabilityBatchCreateRequest(BaseModel):
    crop: str = Field(..., description="Name of the harvested crop")
    quantity: float = Field(..., description="Amount harvested")
    unit: str = Field("kg", description="Unit of measure")
    inputs_used: dict | list[str] | None = Field(None, description="Inputs and materials used in production")
    certification_status: str = Field("unverified", description="Certification status of this batch")
    qr_code_url: str | None = Field(None, description="Optional QR code URL for this batch")

class TraceabilityBatchResponse(BaseModel):
    id: str
    user_id: str
    crop: str
    quantity: float
    unit: str
    prev_hash: str | None
    current_hash: str
    inputs_used: dict | list[str] | None
    harvest_date: datetime
    certification_status: str
    qr_code_url: str | None
    created_at: datetime

@router.post("/batches", response_model=TraceabilityBatchResponse)
async def create_harvest_batch(
    payload: TraceabilityBatchCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new harvest batch record for traceability."""
    try:
        user_id = current_user.external_id

        last_batch_result = await db.execute(
            select(HarvestBatch)
            .where(HarvestBatch.user_id == user_id)
            .order_by(HarvestBatch.created_at.desc())
            .limit(1)
        )
        last_batch = last_batch_result.scalars().first()
        prev_hash = last_batch.current_hash if last_batch else None

        raw_hash_input = f"{user_id}|{payload.crop}|{payload.quantity}|{payload.unit}|{payload.inputs_used}|{payload.certification_status}|{datetime.utcnow().isoformat()}"
        current_hash = hashlib.sha256(raw_hash_input.encode("utf-8")).hexdigest()

        batch = HarvestBatch(
            user_id=user_id,
            crop=payload.crop,
            quantity=payload.quantity,
            unit=payload.unit,
            prev_hash=prev_hash,
            current_hash=current_hash,
            inputs_used=payload.inputs_used,
            certification_status=payload.certification_status,
            qr_code_url=payload.qr_code_url,
            harvest_date=datetime.utcnow()
        )

        db.add(batch)
        await db.commit()
        await db.refresh(batch)

        return TraceabilityBatchResponse(
            id=batch.id,
            user_id=batch.user_id,
            crop=batch.crop,
            quantity=batch.quantity,
            unit=batch.unit,
            prev_hash=batch.prev_hash,
            current_hash=batch.current_hash,
            inputs_used=batch.inputs_used,
            harvest_date=batch.harvest_date,
            certification_status=batch.certification_status,
            qr_code_url=batch.qr_code_url,
            created_at=batch.created_at,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create traceability batch: {e}")

@router.get("/batches/{batch_id}", response_model=TraceabilityBatchResponse)
async def get_harvest_batch(
    batch_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve a harvest batch by ID."""
    result = await db.execute(select(HarvestBatch).where(HarvestBatch.id == batch_id))
    batch = result.scalars().first()
    if not batch or batch.user_id != current_user.external_id:
        raise HTTPException(status_code=404, detail="Harvest batch not found")

    return TraceabilityBatchResponse(
        id=batch.id,
        user_id=batch.user_id,
        crop=batch.crop,
        quantity=batch.quantity,
        unit=batch.unit,
        prev_hash=batch.prev_hash,
        current_hash=batch.current_hash,
        inputs_used=batch.inputs_used,
        harvest_date=batch.harvest_date,
        certification_status=batch.certification_status,
        qr_code_url=batch.qr_code_url,
        created_at=batch.created_at,
    )
