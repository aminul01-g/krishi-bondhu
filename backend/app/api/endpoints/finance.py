from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import logging
from app.db import get_db_session
from app.models.db_models import InsuranceQuote
# from app.crews.krishi_crew import KrishiCrewOrchestrator  # Lazy import to avoid circular deps
from app.tools.finance_tool import CreditScoringTool

logger = logging.getLogger(__name__)
router = APIRouter()

# orchestrator = KrishiCrewOrchestrator()  # Lazy import to avoid circular deps
# credit_scorer = CreditScoringTool()

@router.post("/schemes")
async def get_subsidy_schemes(
    user_id: str,
    crop: str = "All",
    land_size: float = 0.0
):
    try:
        input_text = f"Find eligible subsidy schemes for crop {crop} with land size {land_size}."
        initial_state = {
            "transcript": "Finance request: " + input_text,
            "user_id": user_id
        }
        result = await orchestrator.ainvoke(initial_state)
        return {"advice": result.get("reply_text", "No schemes found.")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/credit-report")
async def get_credit_report(
    user_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Calculate real credit readiness score based on farm diary data.
    Returns score (0-100), breakdown, and personalized recommendations.
    """
    try:
        logger.info(f"Credit report requested for user: {user_id}")
        
        # Use real credit scoring logic
        score_result = await credit_scorer.calculate_credit_score(session, user_id)
        
        return {
            "user_id": user_id,
            "credit_score": score_result.get("score", 0),
            "breakdown": score_result.get("breakdown", {}),
            "metrics": score_result.get("metrics", {}),
            "recommendation": score_result.get("recommendation", ""),
            "message": score_result.get("message", "")
        }
    except Exception as e:
        logger.error(f"Error generating credit report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate credit report.")

@router.post("/insurance-quote")
async def get_insurance_quote(
    user_id: str,
    crop: str,
    land_size: float,
    session: AsyncSession = Depends(get_db_session)
):
    try:
        input_text = f"Get insurance quote for {crop} with {land_size} decimals."
        initial_state = {
            "transcript": "Finance request: " + input_text,
            "user_id": user_id
        }
        result = await orchestrator.ainvoke(initial_state)
        advice = result.get("reply_text", "No quote available.")

        # Log quote
        quote = InsuranceQuote(
            user_id=user_id,
            crop=crop,
            land_size=land_size
        )
        session.add(quote)
        await session.commit()

        return {"quote": advice}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
