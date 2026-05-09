from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.services.recommendation_service import RecommendationService
from app.models.db_models import User
from app.core.dependencies import get_current_user
from app.crews.krishi_crew import KrishiCrew
from app.agents.agronomist_expert import agronomist_expert
from crewai import Task
import asyncio

router = APIRouter()
rec_service = RecommendationService()

@router.get("/personalized")
async def get_personalized_recommendations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch personalized agricultural advice based on the user's soil and irrigation logs.
    Combines deterministic service data with AI reasoning.
    """
    try:
        user_id = current_user.external_id

        # 1. Get raw recommendation data from service layer (deterministic)
        raw_recs = await rec_service.get_personalized_recommendations(db, user_id)
        if "error" in raw_recs:
            raise HTTPException(status_code=500, detail=raw_recs["error"])

        # 2. Use Agronomist Agent to refine these into a conversational, supportive plan
        rec_task = Task(
            description=f"Refine the following raw agricultural recommendations for the farmer: {raw_recs}. Convert them into a supportive, step-by-step guide in Bengali/English, explaining the 'why' behind each suggestion.",
            expected_output="A personalized and encouraging agricultural guidance report.",
            agent=agronomist_expert
        )

        crew_obj = KrishiCrew()
        crew = crew_obj.create_crew(tasks=[rec_task])

        inputs = {
            "user_input": "Give me my personalized farming recommendations.",
            "user_id": user_id,
            "raw_data": raw_recs
        }

        ai_advice = await asyncio.to_thread(crew.kickoff, inputs=inputs)

        return {
            "raw_metrics": raw_recs,
            "personalized_advice": str(ai_advice)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
