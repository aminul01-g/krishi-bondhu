from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.crews.krishi_crew import KrishiCrewOrchestrator
import logging

logger = logging.getLogger("MarketAPI")
router = APIRouter()

# Instantiate the orchestrator for targeted market crew usage
# Note: In a real app we might inject this as a dependency to reuse the cache
orchestrator = KrishiCrewOrchestrator()

class MarketAdviceResponse(BaseModel):
    crop: str
    advice: str

@router.get("/advice", response_model=MarketAdviceResponse)
async def get_market_advice(
    crop: str = Query(..., description="The name of the crop to analyze"),
    lat: float = Query(None, description="Latitude for local mandi search"),
    lon: float = Query(None, description="Longitude for local mandi search")
):
    """
    Dedicated endpoint for fetching real-time market prices, predictions,
    and arbitrage advice for a specific crop.
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
        
        return MarketAdviceResponse(
            crop=crop,
            advice=advice_text
        )
        
    except Exception as e:
        logger.error(f"Error fetching market advice: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while fetching market intelligence.")
