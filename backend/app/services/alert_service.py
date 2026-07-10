import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import select, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import AsyncSessionLocal
from app.models.db_models import Base, User
from app.services.weather_service import WeatherService
from app.services.agronomy_service import AgronomyService

logger = logging.getLogger("AlertService")


class Alert(Base):
    """Persisted proactive pest/disease risk alert (one row per user per run).

    Defined here (not in db_models.py) to keep this module self-contained and
    so importing ``app.services.alert_service`` at startup registers the
    ``alerts`` table on ``Base.metadata`` for ``create_all``.
    """
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    crop = Column(String, nullable=False)
    risk_level = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Alert user={self.user_id} crop={self.crop} level={self.risk_level}>"

class AlertService:
    """
    Production-grade Service for proactively calculating pest and disease risks.
    Replaces simple heuristics with weather-derived risk models and background scheduling.
    """
    def __init__(self):
        self.weather_service = WeatherService()

    async def calculate_pest_risk(self, crop: str, lat: float, lon: float) -> Dict[str, Any]:
        """
        Calculates pest/disease risk using AgronomyService's probability-based
        risk model (disease / drought / pest), guarded so it never throws on
        missing or partial weather payloads.
        """
        weather = await self.weather_service.get_weather_data(lat, lon)
        if not isinstance(weather, dict):
            weather = {}

        # Guard every weather key with a safe default so a partial payload
        # (missing 'temp_mean' / 'humidity' / 'rainfall_mm') can never crash.
        temp = weather.get("temp_mean")
        humidity = weather.get("humidity")
        rainfall = weather.get("rainfall_mm", 0.0) or 0.0
        if temp is None:
            temp = 30.0
        if humidity is None:
            humidity = 80.0

        conditions = {
            "temp": float(temp),
            "humidity": float(humidity),
            "rainfall_mm": float(rainfall),
            "leaf_wetness_hours": 4.0,
        }
        # Delegate to the shared, probability-based risk engine.
        risks = AgronomyService.evaluate_risk(conditions)

        _LEVEL_RANK = {"High": 3, "Moderate": 2, "Medium": 2, "Low": 1}
        alerts: List[str] = []
        highest = 1
        for r in risks:
            lvl = r.get("level", "Low")
            highest = max(highest, _LEVEL_RANK.get(lvl, 1))
            rec = r.get("recommendation")
            if rec:
                alerts.append(rec)

        # General rainfall alert (independent of the probabilistic factors).
        if float(rainfall) > 50:
            alerts.append(
                "Heavy Rainfall: Risk of soil erosion and fungal root rot. "
                "Avoid nitrogen application today."
            )

        if not alerts:
            alerts.append("No specific pest risks detected for current weather and crop.")

        risk_level = {3: "High", 2: "Medium", 1: "Low"}[highest]

        return {
            "crop": crop.lower().strip(),
            "risk_level": risk_level,
            "alerts": alerts,
            "weather_context": {
                "temp": temp,
                "humidity": humidity,
                "rainfall": rainfall,
            },
            "risk_factors": risks,
        }

    async def run_daily_risk_analysis(self):
        """
        Background job to compute risk for all registered users.
        Designed to be called by APScheduler.
        """
        logger.info("Starting daily proactive pest risk analysis for all users...")

        async with AsyncSessionLocal() as db:
            try:
                # 1. Fetch all users
                result = await db.execute(select(User))
                users = result.scalars().all()

                for user in users:
                    # 2. Get user's last known location and current crop from memory/diary
                    # In a real system, this would be stored in a UserProfile table
                    # For now, we use defaults or fetch from the last conversation
                    lat, lon = 23.8103, 90.4125 # Default Dhaka
                    crop = "rice" # Default

                    # 3. Calculate risk
                    risk_data = await self.calculate_pest_risk(crop, lat, lon)

                    # 4. Persist to Alerts table
                    new_alert = Alert(
                        user_id=user.external_id,
                        crop=crop,
                        risk_level=risk_data["risk_level"],
                        message="; ".join(risk_data["alerts"]),
                        timestamp=datetime.utcnow()
                    )
                    db.add(new_alert)

                await db.commit()
                logger.info(f"Successfully processed risk alerts for {len(users)} users.")
            except Exception as e:
                logger.error(f"Daily risk analysis job failed: {e}")
                await db.rollback()
