from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
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


class PricePoint(BaseModel):
    date: str
    price: float


class MarketAdviceResponse(BaseModel):
    crop: str
    advice: str
    current_avg: Optional[float] = None
    predicted_7day: Optional[float] = None
    trend: Optional[str] = None
    trend_direction: Optional[str] = None   # "up" | "down" | "flat"
    trend_percent: Optional[float] = None
    confidence: Optional[str] = None
    price_history: Optional[List[PricePoint]] = Field(default=None)   # last 14 days
    price_forecast: Optional[List[PricePoint]] = Field(default=None)  # next 7 days


class FlashCropSummary(BaseModel):
    crop: str
    current_price: float
    trend_direction: str   # "up" | "down" | "flat"


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
    Returns price_history and price_forecast arrays for chart rendering.
    """
    try:
        logger.info(f"Market advice requested for crop: {crop} at {lat},{lon}")

        gps_data = {"lat": lat, "lon": lon} if lat is not None and lon is not None else None

        # Use the specialized MarketAnalysisCrew
        from crewai import Task
        from app.agents.market_advisor import market_advisor

        market_task = Task(
            description=f"Provide a detailed market analysis and selling advice for {crop}. Use current prices and 7-day predictions.",
            expected_output="A markdown formatted market intelligence report with top 3 mandis, predicted trend, and clear advice on whether to sell or hold.",
            agent=market_advisor
        )

        crew_obj = MarketAnalysisCrew()
        crew = crew_obj.create_crew(tasks=[market_task])

        inputs = {
            "crop": crop,
            "gps": gps_data,
            "user_id": current_user.external_id
        }

        import asyncio
        result = await asyncio.to_thread(crew.kickoff, inputs=inputs)
        advice_text = str(result)

        # Fetch price trend data including history and forecast arrays
        prediction = None
        try:
            prices_data = await market_service.get_current_prices(crop, lat, lon)
            prediction = await market_service.predict_price_trend(crop, session)
            await market_service.save_prices_to_db(session, {
                "crop": crop,
                "current_prices": prices_data.get("current_prices", []),
                "prediction_7day": prediction.get("predicted_7day"),
                "trend": prediction.get("trend")
            })
        except Exception as e:
            logger.warning(f"Failed to persist market prices (db/redis error): {e}")

        return MarketAdviceResponse(
            crop=crop,
            advice=advice_text,
            current_avg=prediction.get("current_avg") if prediction else None,
            predicted_7day=prediction.get("predicted_7day") if prediction else None,
            trend=prediction.get("trend") if prediction else None,
            trend_direction=prediction.get("trend_direction") if prediction else None,
            trend_percent=prediction.get("trend_percent") if prediction else None,
            confidence=prediction.get("confidence") if prediction else None,
            price_history=prediction.get("price_history") if prediction else None,
            price_forecast=prediction.get("price_forecast") if prediction else None,
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


@router.get("/flash", response_model=List[FlashCropSummary])
async def get_flash_prices(
    current_user: User = Depends(get_current_user),
    crops: str = Query(..., description="Comma-separated list of crop names, e.g. ধান,পাট"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Quick multi-crop price summary for the dashboard.
    Accepts a comma-separated list of crops and returns current price + trend direction for each.
    Example: GET /api/market/flash?crops=ধান,পাট,আলু
    """
    try:
        crop_list = [c.strip() for c in crops.split(",") if c.strip()]
        if not crop_list:
            raise HTTPException(status_code=400, detail="At least one crop name is required.")
        if len(crop_list) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 crops per request.")

        summaries: List[FlashCropSummary] = []
        for crop_name in crop_list:
            try:
                prediction = await market_service.predict_price_trend(crop_name, session)
                summaries.append(FlashCropSummary(
                    crop=crop_name,
                    current_price=prediction.get("current_avg", 0.0),
                    trend_direction=prediction.get("trend_direction", "flat"),
                ))
            except Exception as e:
                logger.warning(f"Flash price failed for {crop_name}: {e}")
                summaries.append(FlashCropSummary(
                    crop=crop_name,
                    current_price=0.0,
                    trend_direction="flat",
                ))

        return summaries

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching flash prices: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve flash price summaries.")
