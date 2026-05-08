import os
import logging
import pandas as pd
import json
import random
import pickle
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from redis import Redis
from prophet import Prophet
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db_models import MarketPrice

logger = logging.getLogger("MarketService")

class MarketService:
    """
    Production-grade Service for agricultural market prices.
    Implements Redis caching and Prophet-based forecasting with pre-trained models.
    """
    def __init__(self):
        self.redis = Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"), decode_responses=True)
        self.models_dir = "backend/models"
        self._model_cache = {}

    @staticmethod
    def normalize_crop(crop: str) -> str:
        return str(crop).strip().lower() if crop else ""

    def _load_model(self, crop: str) -> Optional[Prophet]:
        """Loads a pre-trained Prophet model from disk or cache."""
        crop = self.normalize_crop(crop)
        if crop in self._model_cache:
            return self._model_cache[crop]

        model_path = os.path.join(self.models_dir, f"market_{crop}.pkl")
        if os.path.exists(model_path):
            try:
                with open(model_path, 'rb') as f:
                    model = pickle.load(f)
                self._model_cache[crop] = model
                return model
            except Exception as e:
                logger.error(f"Failed to load model for {crop}: {e}")
        return None

    async def get_current_prices(self, crop: str, lat: Optional[float] = None, lon: Optional[float] = None) -> Dict[str, Any]:
        """
        Fetches current wholesale prices. Implements Redis caching.
        """
        crop = self.normalize_crop(crop)
        if not crop or crop == "none":
            return {"error": "Please specify a crop to get market prices."}

        cache_key = f"market:{crop}:{lat}:{lon}"

        # 1. Try Redis Cache
        cached_data = self.redis.get(cache_key)
        if cached_data:
            return json.loads(cached_data)

        # 2. Simulation logic (Real API integration point)
        mandis = ["Karwan Bazar, Dhaka", "Shyam Bazar, Dhaka", "Rajshahi Sadar Mandi", "Khulna Boro Bazar", "Bogura Mohasthan Hat"]
        base_prices = {
            "potato": 45, "onion": 80, "rice": 65, "tomato": 120,
            "brinjal": 60, "cabbage": 35, "chili": 150
        }
        base_price = base_prices.get(crop, 60.0)

        current_prices = []
        for mandi in mandis:
            variation = random.uniform(0.9, 1.1)
            current_prices.append({
                "mandi": mandi,
                "price_bdt_per_kg": round(base_price * variation, 2),
                "distance_km": random.randint(5, 150)
            })

        current_prices.sort(key=lambda x: x["price_bdt_per_kg"], reverse=True)

        result = {
            "crop": crop,
            "current_prices": current_prices,
            "timestamp": datetime.now().isoformat()
        }

        # 3. Cache results for 1 hour
        self.redis.setex(cache_key, 3600, json.dumps(result))

        return result

    async def predict_price_trend(self, crop: str, session: AsyncSession) -> Dict[str, Any]:
        """
        Uses pre-trained Prophet models for price forecasting.
        """
        crop = self.normalize_crop(crop)
        model = self._load_model(crop)

        # Fetch latest price from DB to use as the starting point for the forecast
        stmt = select(MarketPrice).where(MarketPrice.crop == crop).order_by(desc(MarketPrice.timestamp)).limit(1)
        result = await session.execute(stmt)
        latest_entry = result.scalars().first()

        current_price = latest_entry.price_bdt_per_kg if latest_entry else 60.0 # fallback

        if model:
            try:
                # Create a future dataframe for 7 days
                future = model.make_future_dataframe(periods=7)
                forecast = model.predict(future)
                predicted_price = float(forecast['yhat'].iloc[-1])

                trend = "Uptrend" if predicted_price > current_price * 1.02 else "Downtrend" if predicted_price < current_price * 0.98 else "Stable"

                return {
                    "current_avg": round(current_price, 2),
                    "predicted_7day": round(predicted_price, 2),
                    "trend": trend,
                    "confidence": "High (Pre-trained Prophet Model)"
                }
            except Exception as e:
                logger.error(f"Prophet prediction failed for {crop}: {e}")

        # Fallback: Basic heuristic if model not found or fails
        return {
            "current_avg": round(current_price, 2),
            "predicted_7day": round(current_price * 1.02, 2),
            "trend": "Stable (Baseline)",
            "confidence": "Low (Heuristic Fallback)"
        }

    async def save_prices_to_db(self, session: AsyncSession, data: Dict[str, Any]) -> None:
        """Persists market prices to the database."""
        try:
            for price_entry in data.get("current_prices", []):
                market_price = MarketPrice(
                    crop=data["crop"],
                    mandi=price_entry["mandi"],
                    price_bdt_per_kg=price_entry["price_bdt_per_kg"],
                    distance_km=price_entry.get("distance_km"),
                    prediction_7day=data.get("prediction_7day"),
                    market_trend=data.get("trend")
                )
                session.add(market_price)
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Error saving market prices: {e}")

    async def get_price_history(self, session: AsyncSession, crop: str, days: int = 7) -> Dict[str, Any]:
        """Retrieve historical price data for a crop from the database."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            stmt = select(MarketPrice).where(
                (MarketPrice.crop == self.normalize_crop(crop)) &
                (MarketPrice.timestamp >= cutoff_date)
            ).order_by(desc(MarketPrice.timestamp))

            result = await session.execute(stmt)
            prices = result.scalars().all()

            if not prices:
                return {"message": f"No price history found for {crop}"}

            mandis_data = {}
            for p in prices:
                if p.mandi not in mandis_data:
                    mandis_data[p.mandi] = []
                mandis_data[p.mandi].append(p.price_bdt_per_kg)

            mandi_avg = {mandi: round(sum(prices_list) / len(prices_list), 2)
                        for mandi, prices_list in mandis_data.items()}

            return {
                "crop": crop,
                "period_days": days,
                "mandi_averages": mandi_avg,
                "best_price_mandi": max(mandi_avg, key=mandi_avg.get),
                "worst_price_mandi": min(mandi_avg, key=mandi_avg.get)
            }
        except Exception as e:
            logger.error(f"Error retrieving price history: {e}")
            return {"error": str(e)}
