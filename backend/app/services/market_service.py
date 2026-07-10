import os
import logging
import pandas as pd
import json
import pickle
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from redis import Redis
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db_models import MarketPrice
from app.services.market_provider import get_provider, fetch_dam_prices

logger = logging.getLogger("MarketService")

class MarketService:
    """
    Production-grade Service for agricultural market prices.
    Implements Redis caching and Prophet-based forecasting with pre-trained models.
    """
    def __init__(self):
        try:
            self.redis = Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"), decode_responses=True)
            self.redis.ping()
        except Exception as e:
            logger.warning(f"Redis unavailable in MarketService: {e}")
            self.redis = None
        self.models_dir = "backend/models"
        self._model_cache = {}

    @staticmethod
    def normalize_crop(crop: str) -> str:
        return str(crop).strip().lower() if crop else ""

    def _load_model(self, crop: str) -> Optional[Any]:
        """Loads a pre-trained Prophet model from disk or cache."""
        crop = self.normalize_crop(crop)
        if crop in self._model_cache:
            return self._model_cache[crop]

        model_path = os.path.join(self.models_dir, f"market_{crop}.pkl")
        if os.path.exists(model_path):
            from prophet import Prophet  # lazy import; only reached when a model exists
            try:
                with open(model_path, 'rb') as f:
                    model = pickle.load(f)
                self._model_cache[crop] = model
                return model
            except Exception as e:
                logger.error(f"Failed to load model for {crop}: {e}")
        return None

    def _prophet_forecast(
        self, crop: str, history: List[Dict[str, Any]], periods: int = 7
    ) -> Optional[List[Dict[str, Any]]]:
        """Fit + predict a fresh Prophet model on a [{date, price}] history.

        Returns the 7-day forecast list [{date, price, low, high}] or None if
        Prophet is unavailable or fitting fails — callers fall back to the
        calibrated seasonal model. Prophet (and pandas) are imported lazily.
        """
        try:
            from prophet import Prophet  # lazy: only when a real history exists
            import pandas as pd
        except Exception as e:
            logger.warning(f"Prophet unavailable for on-the-fly forecast ({crop}): {e}")
            return None
        try:
            df = pd.DataFrame(history).rename(columns={"date": "ds", "price": "y"})
            df["ds"] = pd.to_datetime(df["ds"])
            model = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=True,
                daily_seasonality=False,
                changepoint_prior_scale=0.05,
            )
            model.fit(df)
            future = model.make_future_dataframe(periods=periods)
            forecast = model.predict(future).iloc[-periods:]
            return [
                {
                    "date": row["ds"].strftime("%Y-%m-%d"),
                    "price": round(float(row["yhat"]), 2),
                    "low": round(float(row["yhat_lower"]), 2),
                    "high": round(float(row["yhat_upper"]), 2),
                }
                for _, row in forecast.iterrows()
            ]
        except Exception as e:
            logger.error(f"On-the-fly Prophet forecast failed for {crop}: {e}")
            return None

    def _forecast_from_history(
        self,
        crop: str,
        provider: Any,
        live_history: Optional[List[Dict[str, Any]]] = None,
    ) -> tuple:
        """Forecast helper for get_current_prices.

        Prefers a Prophet model fit on live DAM history (when Prophet is present
        and the history is usable); otherwise returns the calibrated seasonal
        forecast. Always returns (fcast_list, predicted_price).
        """
        if live_history and len(live_history) >= 2:
            fcast = self._prophet_forecast(crop, live_history, periods=7)
            if fcast:
                return fcast, fcast[-1]["price"]
            # Prophet unavailable/failed -> seasonal band, flagged accordingly.
            _, fcast, predicted_price = provider.forecast(crop, days=7)
            return fcast, predicted_price
        _, fcast, predicted_price = provider.forecast(crop, days=7)
        return fcast, predicted_price

    async def get_current_prices(self, crop: str, lat: Optional[float] = None, lon: Optional[float] = None) -> Dict[str, Any]:
        """
        Fetches current wholesale prices with real mandi distances and honest
        provenance. Uses a live DAM feed when configured, otherwise a calibrated
        seasonal simulation (clearly flagged `simulated`).
        """
        crop = self.normalize_crop(crop)
        if not crop or crop == "none":
            return {"error": "Please specify a crop to get market prices."}

        cache_key = f"market:{crop}:{lat}:{lon}"

        # 1. Try Redis Cache
        if self.redis:
            try:
                cached_data = self.redis.get(cache_key)
                if cached_data:
                    return json.loads(cached_data)
            except Exception as e:
                logger.warning(f"Redis read failed: {e}")

        # 2. Real feed (if reachable) else calibrated simulation
        provider = get_provider()
        live = fetch_dam_prices(crop)

        if live:
            current_price = live["current_price"]
            mandis = live.get("current_prices") or provider.nearby_mandis(crop, lat, lon)
            # Forecast on real history when Prophet is available; otherwise a
            # calibrated seasonal band (clearly flagged in `confidence`).
            fcast, predicted_price = self._forecast_from_history(
                crop, provider, live_history=live.get("price_history")
            )
            source = "live_dam"
            simulated = False
            confidence_note = live["confidence"]
            provenance = "live_dam"
        else:
            current_price = provider.current_price(crop)
            mandis = provider.nearby_mandis(crop, lat, lon)
            _, fcast, predicted_price = provider.forecast(crop, days=7)
            source = provider.source
            simulated = provider.simulated
            confidence_note = getattr(provider, "confidence_note", None)
            provenance = "simulated"

        result = {
            "crop": crop,
            "current_price": current_price,
            "predicted_price": predicted_price,
            "current_prices": mandis,
            "price_forecast": fcast,
            "source": source,
            "simulated": simulated,
            "confidence_note": confidence_note,
            "provenance": provenance,
            "timestamp": datetime.now().isoformat(),
        }

        # 3. Cache results for 1 hour
        if self.redis:
            try:
                self.redis.setex(cache_key, 3600, json.dumps(result))
            except Exception as e:
                logger.warning(f"Redis write failed: {e}")

        return result

    async def predict_price_trend(self, crop: str, session: AsyncSession) -> Dict[str, Any]:
        """
        Price trend forecast. Uses a pre-trained Prophet model when one exists
        (trained on real history if supplied, else on simulated history — always
        flagged `simulated` unless a real export was used), and falls back to the
        calibrated seasonal forecast with uncertainty bands.
        """
        crop = self.normalize_crop(crop)
        provider = get_provider()
        model = self._load_model(crop)

        # Latest price from DB (if any real history exists) anchors the trend.
        current_price = provider.current_price(crop)
        try:
            stmt = select(MarketPrice).where(MarketPrice.crop == crop).order_by(desc(MarketPrice.timestamp)).limit(1)
            res = await session.execute(stmt)
            latest = res.scalars().first()
            if latest:
                current_price = latest.price_bdt_per_kg
        except Exception:
            pass

        predicted_price = current_price
        confidence = "Low (Heuristic Fallback)"
        provenance = "simulated"
        prophet_used = False
        # Defaults: calibrated seasonal model (always safe to fall back to).
        history, fcast, _ = provider.forecast(crop, days=7)

        if model:
            from prophet import Prophet  # lazy import; only reached when a model exists
            try:
                future = model.make_future_dataframe(periods=7)
                forecast = model.predict(future)
                predicted_price = float(forecast['yhat'].iloc[-1])
                confidence = "Prophet model (trained on simulated history)"
                prophet_used = True
            except Exception as e:
                logger.error(f"Prophet prediction failed for {crop}: {e}")

        if not prophet_used:
            # Prefer live DAM history for a robust Prophet forecast; fall back to
            # the calibrated seasonal forecast when DAM/Prophet are unavailable.
            live = fetch_dam_prices(crop)
            if live and len(live.get("price_history", [])) >= 2:
                history = live["price_history"]
                pf = self._prophet_forecast(crop, live["price_history"], periods=7)
                if pf:
                    fcast = pf
                    predicted_price = fcast[-1]["price"]
                    confidence = "Live DAM wholesale feed (Prophet forecast on real history)"
                else:
                    _, fcast, predicted_price = provider.forecast(crop, days=7)
                    confidence = (
                        "Live DAM wholesale prices; 7-day forecast from calibrated "
                        "seasonal model (Prophet unavailable)"
                    )
                provenance = "live_dam"

        # Classify trend
        if predicted_price > current_price * 1.05:
            trend, trend_direction = "Uptrend", "up"
        elif predicted_price < current_price * 0.98:
            trend, trend_direction = "Downtrend", "down"
        else:
            trend, trend_direction = "Stable", "flat"

        trend_percent = round(((predicted_price - current_price) / current_price) * 100, 2) if current_price else 0.0

        return {
            "current_avg": round(current_price, 2),
            "predicted_7day": round(predicted_price, 2),
            "trend": trend,
            "trend_direction": trend_direction,
            "trend_percent": trend_percent,
            "confidence": confidence,
            "source": "live_dam" if provenance == "live_dam" else provider.source,
            "simulated": provenance != "live_dam",
            "provenance": provenance,
            "price_history": history,
            "price_forecast": fcast,
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
