from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db_session
from app.services.market_service import MarketService
from app.core.dependencies import get_current_user
from app.models.db_models import User
from app.crews.krishi_crew import MarketAnalysisCrew
import logging

router = APIRouter()
logger = logging.getLogger("market_api")
market_service = MarketService()

class MarketAdviceResponse(BaseModel):
    crop: str
    advice: str

@router.get("/advice", response_model=MarketAdviceResponse)
async def get_market_advice(
    current_user: User = Depends(get_current_user),
    crop: str = Query(..., description="The name of the crop to analyze"),
    lat: float = Query(None, description="Latitude for local mandi search"),
    lon: float = Query(None, description="Longitude for local mandi search"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Dedicated endpoint for fetching real-time market prices, predictions,
    and arbitrage advice for a specific crop. Prices are persisted for historical tracking.
    """
    try:
        logger.info(f"Market advice requested for crop: {crop} at {lat},{lon}")

        gps_data = {"lat": lat, "lon": lon} if lat is not None and lon is not None else None

        # Use the specialized MarketAnalysisCrew instead of the global orchestrator
        crew_obj = MarketAnalysisCrew()
        crew = crew_obj.create_crew()

        # We define a specific task for this request since we are bypassing the router
        from crewai import Task
        from app.agents.market_advisor import market_advisor

        market_task = Task(
            description=f"Provide a detailed market analysis and selling advice for {crop}. Use current prices and 7-day predictions.",
            expected_output="A markdown formatted market intelligence report with top 3 mandis, predicted trend, and clear advice on whether to sell or hold.",
            agent=market_advisor
        )

        inputs = {
            "crop": crop,
            "gps": gps_data,
            "user_id": current_user.external_id
        }

        # Execute the crew
        import asyncio
        result = await asyncio.to_thread(crew.kickoff, inputs=inputs, tasks=[market_task])
        advice_text = str(result)

        # Persist market prices using the service layer
        try:
            prices_data = await market_service.get_current_prices(crop, lat, lon)
            prediction = await market_service.predict_price_trend(crop, session)
            await market_service.save_prices_to_db(session, {
                "crop": crop,
                "current_prices": prices_data["current_prices"],
                "prediction_7day": prediction.get("predicted_7day"),
                "trend": prediction.get("trend")
            })
        except Exception as e:
            logger.warning(f"Failed to persist market prices: {e}")

        return MarketAdviceResponse(
            crop=crop,
            advice=advice_text
        )

    except Exception as e:
        logger.error(f"Error fetching market advice: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while fetching market intelligence.")

@router.get("/history")
async def get_price_history(
    current_user: User = Depends(get_current_user),
    crop: str = Query(..., description="The name of the crop"),
    days: int = Query(7, description="Number of days of history to retrieve"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve historical market price data for a crop over the specified period.
    """
    try:
        logger.info(f"Price history requested for crop: {crop}, days: {days}")
        history = await market_service.get_price_history(session, crop, days)
        return history
    except Exception as e:
        logger.error(f"Error fetching price history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve price history.")
