from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import logging
from app.db import get_db
from app.models.db_models import IrrigationLog
# from app.crews.krishi_crew import KrishiCrewOrchestrator  # Lazy import to avoid circular deps

logger = logging.getLogger(__name__)
router = APIRouter()

from app.core.dependencies import orchestrator

class WaterAdviceRequest(BaseModel):
    user_id: str
    lat: float
    lon: float
    crop: str = "Rice"

class WaterAdviceResponse(BaseModel):
    advice: str
    moisture_index: Optional[float] = None
    log_id: str

@router.post("/advice", response_model=WaterAdviceResponse)
async def get_irrigation_advice(request: WaterAdviceRequest, db: AsyncSession = Depends(get_db)):
    try:
        # Construct the natural language input for the Water Advisor
        input_text = f"Provide irrigation advice for {request.crop} at coordinates ({request.lat}, {request.lon})."
        
        initial_state = {
            "transcript": "Water advice request: " + input_text,
            "gps": {"lat": request.lat, "lon": request.lon},
            "image_path": None
        }

        result = await orchestrator.ainvoke(initial_state)
        advice = result.get("reply_text", "Could not generate irrigation advice.")

        # Extract moisture index if present in agent thoughts or tools (mocked for now)
        # In a more advanced version, we'd pull this from the tool's structured output
        moisture_index = 0.45 # Placeholder

        # Save to DB
        new_log = IrrigationLog(
            id=str(uuid.uuid4()),
            user_id=request.user_id,
            soil_moisture_index=moisture_index,
            advice=advice
        )
        db.add(new_log)
        await db.commit()
        await db.refresh(new_log)

        return WaterAdviceResponse(
            advice=advice, 
            moisture_index=moisture_index, 
            log_id=new_log.id
        )

    except Exception as e:
        logger.error(f"Irrigation advice failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate irrigation advice")
