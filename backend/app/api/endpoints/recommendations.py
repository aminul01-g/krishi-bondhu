from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
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

@router.get("/recommendations")
async def get_recommendations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    lat: float = Query(None, description="Latitude (used if a farmer profile has no GPS)"),
    lon: float = Query(None, description="Longitude (used if a farmer profile has no GPS)"),
    language: str = Query("bn", description="Response language code, e.g. bn | en"),
):
    """
    Fuses soil, irrigation, weather, water-balance, pest, diary, and market signals
    into a prioritized, explainable advisory list for the farmer.

    GPS is taken from the authenticated user's farmer profile when available;
    otherwise optional lat/lon query params are used. `language` defaults to "bn".
    Async service method — must be awaited.
    """
    try:
        user_id = current_user.external_id

        # Prefer GPS from the farmer profile; fall back to explicit lat/lon params.
        gps = None
        farmer_profile = None
        try:
            from app.models.db_models import FarmerProfile
            prof_result = await db.execute(
                select(FarmerProfile).where(FarmerProfile.user_id == current_user.id)
            )
            farmer_profile = prof_result.scalars().first()
        except Exception:
            farmer_profile = None

        if farmer_profile is not None and getattr(farmer_profile, "latitude", None) is not None:
            gps = {
                "lat": float(farmer_profile.latitude),
                "lon": float(farmer_profile.longitude),
            }
        elif lat is not None and lon is not None:
            gps = {"lat": lat, "lon": lon}

        result = await rec_service.get_personalized_recommendations(
            db, user_id, gps=gps, language=language
        )
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
