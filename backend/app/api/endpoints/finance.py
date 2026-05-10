from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from app.db import get_db
from app.models.db_models import InsuranceQuote, User
from app.core.dependencies import get_current_user
from app.services.finance_service import FinanceService
from app.crews.krishi_crew import FinancialPlanningCrew
import asyncio

logger = logging.getLogger(__name__)
router = APIRouter()
finance_service = FinanceService()

class SubsidyRequest(BaseModel):
    crop: str = "All"
    land_size: float = 0.0

class InsuranceQuoteRequest(BaseModel):
    crop: str = Field(..., min_length=1, description="Name of the crop")
    land_size: float = Field(..., gt=0)

@router.post("/schemes", response_model=dict)
async def get_subsidy_schemes(
    request: SubsidyRequest,
    current_user: User = Depends(get_current_user)
):
    try:
        # Use specialized FinancialPlanningCrew
        from crewai import Task
        from app.agents.finance_advisor import finance_advisor

        subsidy_task = Task(
            description=f"Find eligible government subsidies for crop {request.crop} with land size {request.land_size} decimals. Explain the application process clearly in Bengali.",
            expected_output="A formatted list of eligible schemes with clear 'How to Apply' steps in Bengali.",
            agent=finance_advisor
        )

        crew_obj = FinancialPlanningCrew()
        crew = crew_obj.create_crew(tasks=[subsidy_task])

        inputs = {
            "user_input": f"I am looking for subsidies for {request.crop} on {request.land_size} decimals of land.",
            "user_id": current_user.external_id
        }

        result = await asyncio.to_thread(crew.kickoff, inputs=inputs)
        return {"advice": str(result)}
    except Exception as e:
        logger.error(f"Error fetching subsidies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/credit-report")
async def get_credit_report(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Calculate real credit readiness score based on farm diary data.
    """
    try:
        user_id = current_user.external_id
        logger.info(f"Credit report requested for user: {user_id}")

        # Use the high-precision FinanceService directly for the report
        score_result = await finance_service.calculate_credit_score(session, user_id)

        return {
            "user_id": user_id,
            "credit_score": score_result.get("score", 0),
            "breakdown": score_result.get("breakdown", {}),
            "recommendation": score_result.get("recommendation", ""),
            "message": score_result.get("message", "")
        }
    except Exception as e:
        logger.error(f"Error generating credit report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate credit report.")

@router.post("/insurance-quote")
async def get_insurance_quote(
    request: InsuranceQuoteRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    try:
        user_id = current_user.external_id

        if not request.crop or not request.crop.strip():
            logger.warning(f"Insurance quote requested without valid crop by user {user_id}")
            raise HTTPException(status_code=400, detail="The 'crop' field is required.")

        # Get the structured quote from service
        quote_data = finance_service.get_insurance_quote(request.crop, request.land_size)

        # Use FinancialPlanningCrew to explain the quote in a supportive way
        from crewai import Task
        from app.agents.finance_advisor import finance_advisor

        insurance_task = Task(
            description=f"Explain this insurance quote to the farmer: {quote_data}. Emphasize the payout triggers for {request.crop}.",
            expected_output="A friendly explanation of the premium, coverage, and specific disaster triggers in Bengali/English.",
            agent=finance_advisor
        )

        crew_obj = FinancialPlanningCrew()
        crew = crew_obj.create_crew(tasks=[insurance_task])

        inputs = {
            "user_input": f"I want an insurance quote for {request.crop} on {request.land_size} decimals.",
            "user_id": user_id
        }

        result = await asyncio.to_thread(crew.kickoff, inputs=inputs)
        advice = str(result)

        # Log quote to DB
        quote_record = InsuranceQuote(
            user_id=user_id,
            crop=request.crop,
            land_size=request.land_size
        )
        session.add(quote_record)
        await session.commit()

        return {"quote": advice}
    except Exception as e:
        logger.error(f"Insurance quote failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
