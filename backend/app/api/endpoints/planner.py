from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio

from app.db import get_db
from app.core.dependencies import get_current_user
from app.models.db_models import User
from app.models.production_models import SeasonPlan
from app.services.yield_service import predict_yield, generate_season_plan
from app.crews.krishi_crew import KrishiCrew
from app.agents.yield_planner import yield_planner
from crewai import Task

router = APIRouter()

class PlanRequest(BaseModel):
    crop: str
    lat: float
    lon: float

@router.post("/generate")
async def create_season_plan(
    payload: PlanRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generates a comprehensive seasonal crop plan including yield prediction.
    Combines yield service data with YieldPlannerAgent reasoning.
    """
    try:
        # 1. Get raw technical plan and prediction from service
        plan_result = await generate_season_plan(
            db=db,
            user_id=current_user.external_id,
            crop=payload.crop,
            lat=payload.lat,
            lon=payload.lon
        )

        # 2. Use YieldPlannerAgent to turn raw data into a structured, actionable strategy
        crew_obj = KrishiCrew()
        crew = crew_obj.create_crew()

        planning_task = Task(
            description=(
                f"Turn the following raw seasonal plan for {payload.crop} into a high-impact strategy. "
                f"Raw Data: {plan_result}. "
                "Focus on optimal planting dates, fertilizer timing, and risk mitigation. "
                "Provide the output as a a formatted guide for the farmer."
            ),
            expected_output="A comprehensive seasonal crop strategy with a clear timeline and yield-optimization tips.",
            agent=yield_planner
        )

        inputs = {
            "user_input": f"Generate a high-yield plan for {payload.crop}.",
            "user_id": current_user.external_id,
            "raw_plan": plan_result
        }

        ai_strategy = await asyncio.to_thread(crew.kickoff, inputs=inputs, tasks=[planning_task])

        return {
            "status": "success",
            "plan_id": plan_result["plan_id"],
            "technical_details": plan_result["details"],
            "ai_strategy": str(ai_strategy)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate plan: {str(e)}")

@router.get("/my-plans")
async def list_my_plans(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves all seasonal plans for the authenticated user.
    """
    try:
        result = await db.execute(
            select(SeasonPlan).where(SeasonPlan.user_id == current_user.external_id)
        )
        plans = result.scalars().all()
        return [
            {
                "id": p.id,
                "crop": p.crop,
                "year": p.season_year,
                "predicted_yield": p.predicted_yield,
                "confidence": p.confidence_score,
                "details": p.plan_details,
                "status": p.status
            }
            for p in plans
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/forecast")
async def get_yield_forecast(
    crop: str,
    lat: float,
    lon: float,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Provides a quick yield forecast.
    """
    try:
        prediction = await predict_yield(
            db=db,
            user_id=current_user.external_id,
            crop=crop,
            lat=lat,
            lon=lon
        )
        return {
            "crop": crop,
            "forecast": prediction
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
