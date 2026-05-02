from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import logging
from app.db import get_db
from app.models.db_models import SoilTestLog
from app.crews.krishi_crew import KrishiCrewOrchestrator

logger = logging.getLogger(__name__)
router = APIRouter()

# Instantiate the orchestrator once
orchestrator = KrishiCrewOrchestrator()

class SoilAnalyzeRequest(BaseModel):
    user_id: str
    image_url: Optional[str] = None
    diy_inputs: Optional[Dict[str, Any]] = None
    crop: str = "Unknown"

class SoilAnalyzeResponse(BaseModel):
    advice: str
    log_id: str

@router.post("/analyze", response_model=SoilAnalyzeResponse)
async def analyze_soil(request: SoilAnalyzeRequest, db: AsyncSession = Depends(get_db)):
    try:
        # Construct the natural language input to leverage the CrewAI router
        input_text = f"Analyze my soil for crop: {request.crop}."
        if request.diy_inputs:
            input_text += f" I did a DIY test: {request.diy_inputs}."

        initial_state = {
            "transcript": input_text,
            "gps": None,
            "image_path": request.image_url
        }

        # The orchestrator will route to 'soil_scientist_agent' if the intent is recognized as 'soil'
        # Or we can force it by prefixing with an explicit soil request.
        initial_state["transcript"] = "Soil analysis request: " + initial_state["transcript"]

        result = await orchestrator.ainvoke(initial_state)
        advice = result.get("reply_text", "Could not analyze soil.")

        # Save to DB
        new_log = SoilTestLog(
            id=str(uuid.uuid4()),
            user_id=request.user_id,
            crop=request.crop,
            image_url=request.image_url,
            diy_inputs=request.diy_inputs,
            recommendations={"advice": advice}
        )
        db.add(new_log)
        await db.commit()
        await db.refresh(new_log)

        return SoilAnalyzeResponse(advice=advice, log_id=new_log.id)

    except Exception as e:
        logger.error(f"Soil analysis failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze soil")
