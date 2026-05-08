import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import AsyncSessionLocal
from app.models.db_models import User
from app.services.weather_service import WeatherService

logger = logging.getLogger("AlertService")

class AlertService:
    """
    Production-grade Service for proactively calculating pest and disease risks.
    Replaces simple heuristics with weather-derived risk models and background scheduling.
    """
    def __init__(self):
        self.weather_service = WeatherService()

    async def calculate_pest_risk(self, crop: str, lat: float, lon: float) -> Dict[str, Any]:
        """
        Calculates risk using a data-driven approach based on current weather.
        Production: Uses thresholds from agricultural literature (e.g., BPH, Late Blight).
        """
        weather = await self.weather_service.get_weather_data(lat, lon)
        temp = weather['temp_mean']
        humidity = weather['humidity']
        rainfall = weather['rainfall_mm']

        crop = crop.lower().strip()
        risk_level = "Low"
        alerts = []

        # Scientific thresholds for common Bangladeshi pests
        # 1. Rice: Brown Plant Hopper (BPH) - High humidity, moderate temp
        if "rice" in crop or "paddy" in crop:
            if temp >= 25 and humidity >= 80:
                risk_level = "High"
                alerts.append("Brown Plant Hopper (BPH): High risk. High humidity and moderate temps favor hopper multiplication.")
            elif temp >= 25 and humidity >= 70:
                risk_level = "Medium"
                alerts.append("BPH: Conditions are favorable. Monitor the base of the plants.")

        # 2. Potato: Late Blight (Phytophthora infestans) - Cool, wet, humid
        elif "potato" in crop:
            if 10 <= temp <= 24 and humidity >= 85:
                risk_level = "High"
                alerts.append("Late Blight (নাবি ধসা): CRITICAL RISK. Cool, wet conditions are ideal for spore spread.")
            elif 15 <= temp <= 25 and humidity >= 75:
                risk_level = "Medium"
                alerts.append("Late Blight: Moderate risk. Ensure proper drainage and aeration.")

        # 3. Brinjal: Fruit and Shoot Borer - Warm and humid
        elif "brinjal" in crop:
            if temp > 25 and humidity > 60:
                risk_level = "High"
                alerts.append("Fruit and Shoot Borer: High risk. Warm weather accelerates larval growth.")

        # General Rainfall Alert
        if rainfall > 50:
            alerts.append("Heavy Rainfall: Risk of soil erosion and fungal root rot. Avoid nitrogen application today.")

        if not alerts:
            alerts.append("No specific pest risks detected for current weather and crop.")

        return {
            "crop": crop,
            "risk_level": risk_level,
            "alerts": alerts,
            "weather_context": {
                "temp": temp,
                "humidity": humidity,
                "rainfall": rainfall
            }
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
                        timestamp=datetime.now()
                    )
                    db.add(new_alert)

                await db.commit()
                logger.info(f"Successfully processed risk alerts for {len(users)} users.")
            except Exception as e:
                logger.error(f"Daily risk analysis job failed: {e}")
                await db.rollback()
