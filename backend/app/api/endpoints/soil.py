from fastapi import APIRouter, HTTPException, File, UploadFile, Form, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
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


class SoilRecommendation(BaseModel):
    nutrient: str
    action: str
    amount: str
    timing: str
    brand_suggestion: str = ""


class SoilTestRequest(BaseModel):
    """Lab-style NPK + pH soil test values."""
    nitrogen: float = Field(..., ge=0, le=400, description="kg/ha")
    phosphorus: float = Field(..., ge=0, le=100, description="kg/ha")
    potassium: float = Field(..., ge=0, le=400, description="kg/ha")
    ph: float = Field(..., ge=4.0, le=9.0, description="soil pH")
    organic_matter: float = Field(2.0, ge=0, le=8, description="% organic matter")
    crop: str = "ধান"
    district: Optional[str] = None


class SoilTestResponse(BaseModel):
    overall_health: str  # ভালো | মাঝারি | খারাপ
    health_score: int    # 0-100
    n_status: str        # কম | পর্যাপ্ত | বেশি
    p_status: str
    k_status: str
    ph_status: str       # অম্লীয় | নিরপেক্ষ | ক্ষারীয়
    recommendations: List[SoilRecommendation]
    next_test_recommended_days: int


@router.post("/analyze", response_model=SoilTestResponse)
async def analyze_soil_test(
    request: SoilTestRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Analyzes lab-style NPK + pH soil test results.
    Returns an overall health score, per-nutrient status, and actionable
    fertilizer recommendations (deterministic rule-based logic, no LLM call).
    """
    try:
        result = soil_service.analyze_npk(request.model_dump())
        return SoilTestResponse(**result)
    except Exception as e:
        logger.error(f"Soil NPK analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Soil analysis failed.")

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
