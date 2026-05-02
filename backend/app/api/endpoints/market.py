from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
# from app.crews.krishi_crew import KrishiCrewOrchestrator  # Lazy import to avoid circular deps
from app.db import get_db_session
from app.tools.market_tool import MarketPriceTool
import logging

logger = logging.getLogger("MarketAPI")
router = APIRouter()

# Instantiate the orchestrator for targeted market crew usage
from app.core.dependencies import orchestrator
market_tool = MarketPriceTool()

class MarketAdviceResponse(BaseModel):
    crop: str
    advice: str

@router.get("/advice", response_model=MarketAdviceResponse)
async def get_market_advice(
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
        
        gps_data = None
        if lat is not None and lon is not None:
            gps_data = {"lat": lat, "lon": lon}
            
        # We manually structure the prompt to force the KrishiCrew to route to Market Analyst
        # Since we refactored krishi_crew to use JSON routing, we just pass the query.
        initial_state = {
            "transcript": f"Tell me the market price and selling advice for {crop}.",
            "gps": gps_data,
            "image_path": None
        }
        
        # Invoke the orchestrator. It will classify intent='market' and route to the Market Agent.
        result_state = await orchestrator.ainvoke(initial_state)
        
        # The reply_text contains the final markdown advice from the Market Analyst
        advice_text = result_state.get("reply_text", "Failed to retrieve market data.")
        
        # Persist market prices to database
        try:
            await market_tool.save_prices_to_db(session)
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
    crop: str = Query(..., description="The name of the crop"),
    days: int = Query(7, description="Number of days of history to retrieve"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve historical market price data for a crop over the specified period.
    Useful for farmers to see price trends before deciding when to sell.
    """
    try:
        logger.info(f"Price history requested for crop: {crop}, days: {days}")
        history = await market_tool.get_price_history(session, crop, days)
        return history
    except Exception as e:
        logger.error(f"Error fetching price history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve price history.")
