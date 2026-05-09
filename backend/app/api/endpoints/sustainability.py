from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

from app.db import get_db
from app.core.dependencies import get_current_user
from app.models.db_models import User
from app.services.sustainability_service import (
    get_sustainability_scorecard,
    get_carbon_market_opportunities
)
from app.crews.krishi_crew import HealthAndSoilCrew
from app.agents.sustainability_coach import sustainability_coach
from crewai import Task

router = APIRouter()

@router.get("/scorecard")
async def get_scorecard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves the farmer's sustainability score and carbon offset metrics.
    """
    try:
        scorecard = await get_sustainability_scorecard(db, current_user.external_id)
        return {
            "status": "success",
            "data": scorecard
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate scorecard: {str(e)}")

@router.get("/opportunities")
async def get_opportunities(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Matches the farmer's sustainability score to available carbon market opportunities.
    """
    try:
        from app.models.production_models import SustainabilityMetric
        from sqlalchemy import select

        result = await db.execute(
            select(SustainabilityMetric).where(SustainabilityMetric.user_id == current_user.external_id)
        )
        metric = result.scalars().first()

        if not metric:
            scorecard = await get_sustainability_scorecard(db, current_user.external_id)
            score = scorecard["score"]
        else:
            score = metric.carbon_score

        opportunities = await get_carbon_market_opportunities(score, "Bangladesh")

        return {
            "status": "success",
            "score": score,
            "opportunities": opportunities
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch opportunities: {str(e)}")

@router.get("/explain")
async def explain_sustainability(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns a personalized explanation of how the sustainability score is calculated.
    """
    try:
        # Use AI Coach to provide a personalized explanation instead of a static string
        explanation_task = Task(
            description=f"Explain to the farmer how their sustainability score is calculated based on their farm habits. Highlight the impact of synthetic vs organic inputs. Keep it encouraging and educational.",
            expected_output="A supportive and clear explanation in Bengali/English about the sustainability scoring system.",
            agent=sustainability_coach
        )

        crew_obj = HealthAndSoilCrew()
        crew = crew_obj.create_crew(tasks=[explanation_task])

        inputs = {
            "user_input": "How is my sustainability score calculated?",
            "user_id": current_user.external_id
        }

        result = await asyncio.to_thread(crew.kickoff, inputs=inputs)

        return {
            "status": "success",
            "explanation": str(result)
        }
    except Exception as e:
        # Fallback to static text if AI fails
        return {
            "status": "success",
            "explanation": "Your sustainability score is calculated based on your farm diary. Higher scores unlock access to government subsidies and international carbon credits."
        }
