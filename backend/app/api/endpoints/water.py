from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import logging
from app.db import get_db
from app.models.db_models import IrrigationLog, User
from app.core.dependencies import get_current_user
from app.services.weather_service import WeatherService
from app.crews.krishi_crew import KrishiCrew
import asyncio

logger = logging.getLogger(__name__)
router = APIRouter()
weather_service = WeatherService()

from typing import Optional, List, Dict, Any

class IrrigationScheduleDay(BaseModel):
    day: str
    date: str
    irrigate: bool
    amount_mm: float
    reason: str

class WaterAdviceRequest(BaseModel):
    lat: float
    lon: float
    crop: str = "Rice"

class WaterAdviceResponse(BaseModel):
    crop: str
    et0_mm_per_day: float
    moisture_index: float
    current_rainfall_mm: float
    advice: str
    irrigation_schedule: List[IrrigationScheduleDay]
    log_id: str

@router.post("/advice", response_model=WaterAdviceResponse)
async def get_irrigation_advice(
    request: WaterAdviceRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        # Use specialized logic for water balance via the service layer
        # This ensures the Hargreaves-Samani calculations are performed accurately
        water_balance = await weather_service.calculate_water_balance(
            crop=request.crop,
            lat=request.lat,
            lon=request.lon
        )

        if "et0_mm_day" not in water_balance:
            water_balance["et0_mm_day"] = 5.0
            
        # Use the crew to turn the technical balance into a helpful Bengali/English response
        from crewai import Task
        from app.agents.water_advisor import water_advisor

        water_task = Task(
            description=f"Translate the following technical water balance data into an easy-to-understand irrigation advice for a farmer. Data: {water_balance}. User Crop: {request.crop}",
            expected_output="A concise, supportive advice message in Bengali/English telling the farmer exactly how much to irrigate and why.",
            agent=water_advisor
        )

        crew_obj = KrishiCrew()
        crew = crew_obj.create_crew(tasks=[water_task])

        inputs = {
            "user_input": f"I need irrigation advice for my {request.crop} crop.",
            "gps": {"lat": request.lat, "lon": request.lon},
            "user_id": current_user.external_id
        }

        result = await asyncio.to_thread(crew.kickoff, inputs=inputs)
        advice = str(result)

        # Save to DB - Use the actual moisture index from water balance
        moisture_index = water_balance.get("moisture_index", 0.0)

        new_log = IrrigationLog(
            id=str(uuid.uuid4()),
            user_id=current_user.external_id,
            soil_moisture_index=moisture_index,
            advice=advice
        )
        db.add(new_log)
        await db.commit()
        await db.refresh(new_log)

        return WaterAdviceResponse(
            crop=request.crop,
            et0_mm_per_day=water_balance.get("et0_mm_day", 0.0),
            moisture_index=moisture_index,
            current_rainfall_mm=water_balance.get("rainfall_mm", 0.0),
            advice=advice,
            irrigation_schedule=water_balance.get("irrigation_schedule", []),
            log_id=new_log.id
        )

    except Exception as e:
        logger.error(f"Irrigation advice failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate irrigation advice")
