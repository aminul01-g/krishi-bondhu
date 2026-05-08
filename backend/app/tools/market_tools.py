from langchain.tools import BaseTool
from app.services.market_service import MarketService
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Optional

class MarketPriceTool(BaseTool):
    name: str = "Market Price Fetcher and Predictor"
    description: str = "Fetches current wholesale prices for a crop in nearby mandis and provides a 7-day predicted trend."

    # We use a property for the service to avoid initialization issues in Pydantic models
    @property
    def service(self) -> MarketService:
        return MarketService()

    def _run(self, crop: str, location_lat: Optional[float] = None, location_lon: Optional[float] = None, **kwargs) -> str:
        """Synchronous wrapper for market price fetching."""
        import asyncio

        # Create a new event loop to handle the async service calls
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        async def execute():
            # 1. Fetch current prices
            prices_data = await self.service.get_current_prices(crop, location_lat, location_lon)
            if "error" in prices_data:
                return prices_data["error"]

            # We need a DB session for prediction (historical data)
            # In a real app, this session is passed via the agent's context
            # For this wrapper, we attempt to get a session from the app's session local
            from app.db import AsyncSessionLocal
            async with AsyncSessionLocal() as session:
                prediction = await self.service.predict_price_trend(crop, session)

                # Persist the current prices to DB for future Prophet training
                await self.service.save_prices_to_db(session, {
                    "crop": prices_data["crop"],
                    "current_prices": prices_data["current_prices"],
                    "prediction_7day": prediction.get("predicted_7day"),
                    "trend": prediction.get("trend")
                })

                # Format output for the LLM
                output = f"--- MARKET INTELLIGENCE FOR {crop.upper()} ---\n"
                output += "CURRENT WHOLESALE PRICES (BDT/KG):\n"
                for p in prices_data["current_prices"][:3]:
                    output += f"- {p['mandi']}: {p['price_bdt_per_kg']} BDT (Distance: ~{p['distance_km']} km)\n"

                output += "\nPRICE PREDICTION & ARBITRAGE (Next 7 Days):\n"
                output += f"- Current Avg Price: {prediction.get('current_avg')} BDT\n"
                output += f"- Predicted Price (7 days): {prediction.get('predicted_7day')} BDT\n"
                output += f"- Market Trend: {prediction.get('trend')}\n\n"
                output += "Advice: Consider transport costs (avg 2-5 BDT/kg per 50km) before traveling to a distant mandi for a slightly higher price."
                return output

        return loop.run_until_complete(execute())
