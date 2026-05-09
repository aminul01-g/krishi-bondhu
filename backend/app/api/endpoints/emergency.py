from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import logging

from app.db import get_db
from app.core.dependencies import get_current_user
from app.models.db_models import InsuranceQuote, User
from app.services.emergency_service import (
    list_insurance_providers,
    create_damage_report,
    get_damage_report,
    submit_claim,
    log_helpline_call,
)
from app.crews.krishi_crew import EmergencyResponseCrew

logger = logging.getLogger(__name__)
router = APIRouter()

class DamageReportCreate(BaseModel):
    crop_type: str
    growth_stage: Optional[str] = None
    lat: float
    lon: float
    damage_cause: str
    damage_estimate_percent: float
    yield_loss_estimate_percent: float
    insurance_provider_id: Optional[str] = None
    voice_statement_transcribed: Optional[str] = None
    image_data: Optional[List[str]] = None

class ClaimRequest(BaseModel):
    insurance_provider_id: Optional[str] = None

class HelplineRequest(BaseModel):
    crop_type: Optional[str] = None
    damage_estimate: Optional[float] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    call_duration_seconds: Optional[int] = None
    operator_notes: Optional[str] = None
    status: str = Field(default="initiated")

@router.get("/providers")
async def get_providers(db: AsyncSession = Depends(get_db)):
    try:
        return await list_insurance_providers(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reports")
async def create_report(
    payload: DamageReportCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    AI-Powered Damage Assessment.
    Uses EmergencyResponseCrew to generate a structured official report from images and voice.
    """
    try:
        # 1. Use the Specialized Emergency Crew to generate the official report text
        from crewai import Task
        from app.agents.emergency_response import emergency_response

        report_task = Task(
            description=(
                f"Analyze the crop damage for {payload.crop_type}. "
                f"Cause: {payload.damage_cause}. Estimate: {payload.damage_estimate_percent}%. "
                f"Voice testimony: {payload.voice_statement_transcribed}. "
                "Generate a formal a damage assessment report for insurance and government relief."
            ),
            expected_output="A professional, structured damage assessment report including a summary of loss and specific evidence markers.",
            agent=emergency_response
        )

        crew_obj = EmergencyResponseCrew()
        crew = crew_obj.create_crew(tasks=[report_task])

        inputs = {
            "user_id": current_user.external_id,
            "crop": payload.crop_type,
            "gps": {"lat": payload.lat, "lon": payload.lon},
            "evidence": payload.image_data
        }

        # Generate the a-detailed response
        report_text = await asyncio.to_thread(crew.kickoff, inputs=inputs)

        # 2. Save the structured report to the database via Service Layer
        report = await create_damage_report(
            db,
            farmer_id=current_user.external_id,
            crop_type=payload.crop_type,
            growth_stage=payload.growth_stage,
            lat=payload.lat,
            lon=payload.lon,
            damage_cause=payload.damage_cause,
            damage_estimate_percent=payload.damage_estimate_percent,
            yield_loss_estimate_percent=payload.yield_loss_estimate_percent,
            insurance_provider_id=payload.insurance_provider_id,
            voice_statement_transcribed=f"AI Analysis: {str(report_text)}\nOriginal: {payload.voice_statement_transcribed}",
            image_data=payload.image_data,
        )
        return {"id": str(report.id), "status": report.status, "ai_report": str(report_text)}
    except Exception as e:
        logger.error(f"Emergency report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reports/{report_id}")
async def retrieve_report(report_id: str, db: AsyncSession = Depends(get_db)):
    report = await get_damage_report(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Damage report not found")
    return report

@router.post("/reports/{report_id}/claim")
async def claim_report(report_id: str, payload: ClaimRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await submit_claim(db, report_id, payload.insurance_provider_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/helpline")
async def log_call(
    payload: HelplineRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        log = await log_helpline_call(
            db,
            farmer_id=current_user.external_id,
            crop_type=payload.crop_type,
            damage_estimate=payload.damage_estimate,
            lat=payload.lat,
            lon=payload.lon,
            call_duration_seconds=payload.call_duration_seconds,
            operator_notes=payload.operator_notes,
            status=payload.status,
        )
        return {"id": str(log.id), "status": log.status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
