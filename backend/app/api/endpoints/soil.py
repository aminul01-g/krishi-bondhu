from fastapi import APIRouter, HTTPException, File, UploadFile, Form, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db_session
from app.services.soil_service import SoilService
from app.core.dependencies import get_current_user
from app.models.db_models import User
from app.crews.krishi_crew import HealthAndSoilCrew
import logging
import os

router = APIRouter()
logger = logging.getLogger("soil_api")
soil_service = SoilService()

class SoilAnalysisResponse(BaseModel):
    analysis: str
    recommendations: str = None

@router.post("/analyze-image")
async def analyze_soil_image(
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    lat: float = Form(None),
    lon: float = Form(None),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Analyzes soil image using the fallback chain: ViT -> Groq -> Rules.
    """
    try:
        # Save image locally
        from app.api.utils import save_image_local
        image_path = await save_image_local(image)

        # Use specialized HealthAndSoilCrew
        from crewai import Task
        from app.agents.soil_scientist import soil_scientist

        soil_task = Task(
            description=f"Analyze the soil image at {image_path}. Identify texture and organic matter, then provide localized fertilizer advice.",
            expected_output="A detailed soil health report with texture classification and specific nutrient recommendations.",
            agent=soil_scientist
        )

        crew_obj = HealthAndSoilCrew()
        crew = crew_obj.create_crew(tasks=[soil_task])

        inputs = {
            "image_path": image_path,
            "gps": {"lat": lat, "lon": lon},
            "user_id": current_user.external_id
        }

        import asyncio
        result = await asyncio.to_thread(crew.kickoff, inputs=inputs)

        return SoilAnalysisResponse(analysis=str(result))

    except Exception as e:
        logger.error(f"Error analyzing soil image: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while analyzing the soil image.")

@router.post("/interpret-test")
async def interpret_diy_test(
    test_data: str = Form(...),
    crop: str = Form("general"),
    current_user: User = Depends(get_current_user)
):
    """
    Interprets DIY soil test results (Ribbon/pH/Jar).
    """
    try:
        # Use service layer directly for deterministic rule-based logic
        interpretation = soil_service.interpret_diy_test(test_data)
        recommendations = soil_service.recommend_fertilizer(interpretation, crop)

        return SoilAnalysisResponse(
            analysis=interpretation,
            recommendations=recommendations
        )
    except Exception as e:
        logger.error(f"Error interpreting DIY test: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid test data: {str(e)}")
