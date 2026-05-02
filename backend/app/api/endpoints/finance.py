from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import logging
from app.db import get_db
from app.models.db_models import InsuranceQuote
from app.crews.krishi_crew import KrishiCrewOrchestrator

logger = logging.getLogger(__name__)
router = APIRouter()

orchestrator = KrishiCrewOrchestrator()

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
async def get_credit_report(user_id: str):
    try:
        input_text = f"Calculate credit readiness score for user {user_id}."
        initial_state = {
            "transcript": "Finance request: " + input_text,
            "user_id": user_id
        }
        result = await orchestrator.ainvoke(initial_state)
        return {"report": result.get("reply_text", "Could not generate report.")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/insurance-quote")
async def get_insurance_quote(
    user_id: str,
    crop: str,
    land_size: float,
    db: AsyncSession = Depends(get_db)
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
        db.add(quote)
        await db.commit()

        return {"quote": advice}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
