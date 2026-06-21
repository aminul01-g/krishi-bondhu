from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional
from datetime import datetime
import json
import logging
import os

from app.models.db_models import User
from app.core.dependencies import get_current_user
from app.services.weather_service import WeatherService
from app.services.market_service import MarketService
from app.services.alert_service import AlertService

logger = logging.getLogger("dashboard_api")
router = APIRouter()

weather_service = WeatherService()
market_service = MarketService()
alert_service = AlertService()

# Try to initialize Redis for dashboard caching
try:
    from redis import Redis
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    redis_client = Redis.from_url(redis_url, decode_responses=True)
    redis_client.ping()
except Exception as e:
    logger.warning(f"Redis unavailable for dashboard cache: {e}")
    redis_client = None

# In-memory cache fallback
_mem_cache = {}

def get_bangla_date():
    """Very basic approximation of Bangla date or just Gregorian in Bangla numerals."""
    # In a real app, use a proper library like `bengali` for actual BS date conversion.
    # We will just return the Gregorian date translated to Bengali.
    months_bn = ["জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন", "জুলাই", "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর"]
    weekdays_bn = ["সোমবার", "মঙ্গলবার", "বুধবার", "বৃহস্পতিবার", "শুক্রবার", "শনিবার", "রবিবার"]
    
    now = datetime.now()
    day = str(now.day).translate(str.maketrans('0123456789', '০১২৩৪৫৬৭৮৯'))
    year = str(now.year).translate(str.maketrans('0123456789', '০১২৩৪৫৬৭৮৯'))
    month = months_bn[now.month - 1]
    weekday = weekdays_bn[now.weekday()]
    
    return f"{day} {month} {year}", weekday

@router.get("/summary")
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    lat: float = Query(23.8103, description="Latitude (default Dhaka)"),
    lon: float = Query(90.4125, description="Longitude (default Dhaka)"),
    crops: str = Query("ধান", description="Comma separated list of crops")
):
    try:
        user_id = current_user.external_id
        today_str = datetime.now().strftime("%Y-%m-%d")
        cache_key = f"dashboard:{user_id}:{today_str}:{lat}:{lon}:{crops}"

        # 1. Try Cache (15 min TTL)
        if redis_client:
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception:
                pass
        elif cache_key in _mem_cache:
            # Note: in-memory cache TTL not strictly enforced here for simplicity
            return _mem_cache[cache_key]

        # Process crops
        crop_list = [c.strip() for c in crops.split(",") if c.strip()]
        primary_crop = crop_list[0] if crop_list else "ধান"

        # 2. Greeting & Date
        bn_date, bn_weekday = get_bangla_date()
        greeting = {
            "username": current_user.username or "কৃষক বন্ধু",
            "district": "আপনার এলাকা", # Could be fetched via reverse geocoding
            "date_bn": bn_date,
            "weekday_bn": bn_weekday
        }

        # 3. Weather
        weather_data = await weather_service.get_weather_data(lat, lon)
        weather_info = {
            "temp_mean": round(weather_data.get("temp_mean", 30.0), 1),
            "humidity": round(weather_data.get("humidity", 80), 1)
        }

        # 4. Irrigation (based on primary crop)
        water_balance = await weather_service.calculate_water_balance(primary_crop, lat, lon)
        status = water_balance.get("status", "Sufficient")
        
        if status == "Deficit":
            irrigation = {
                "badge": "red",
                "badge_text_bn": "আজ সেচ দিন",
                "advice_bn": "মাটিতে পানির অভাব। দ্রুত সেচ দেওয়া প্রয়োজন।"
            }
        elif status == "Sufficient":
            irrigation = {
                "badge": "yellow",
                "badge_text_bn": "আগামীকাল সেচ দিন",
                "advice_bn": "পানির পরিমাণ স্বাভাবিক। তবে নজর রাখুন।"
            }
        else: # Saturated
            irrigation = {
                "badge": "green",
                "badge_text_bn": "এই সপ্তাহে সেচ লাগবে না",
                "advice_bn": "পর্যাপ্ত পানি আছে। সেচের প্রয়োজন নেই।"
            }

        # 5. Market Flash
        market_flash = []
        for crop in crop_list:
            prices_data = await market_service.get_current_prices(crop, lat, lon)
            if prices_data and "current_prices" in prices_data and prices_data["current_prices"]:
                # Just take the first mandi's price as representative
                price = prices_data["current_prices"][0]["price_bdt_per_kg"]
                
                # Simulate trend (in real app, compare with yesterday)
                import random
                trend_val = random.choice(["up", "down", "flat"])
                
                market_flash.append({
                    "crop_bn": crop,
                    "price_bdt_per_kg": price,
                    "trend": trend_val
                })

        # 6. Alerts
        alerts_list = []
        risk_data = await alert_service.calculate_pest_risk(primary_crop, lat, lon)
        if risk_data and risk_data.get("alerts"):
            for i, alert_text in enumerate(risk_data["alerts"]):
                if alert_text == "No specific pest risks detected for current weather and crop.":
                    continue
                    
                alert_type = "pest"
                if "Rainfall" in alert_text or "weather" in alert_text.lower():
                    alert_type = "weather"
                    
                alerts_list.append({
                    "id": f"alert_{i}",
                    "type": alert_type,
                    "text_bn": alert_text.replace("High risk.", "উচ্চ ঝুঁকি।").replace("Moderate risk.", "মাঝারি ঝুঁকি।") # basic translation if returned in English
                })

        # Assemble final response
        response_data = {
            "greeting": greeting,
            "weather": weather_info,
            "irrigation": irrigation,
            "market_flash": market_flash,
            "alerts": alerts_list
        }

        # Cache it
        if redis_client:
            try:
                redis_client.setex(cache_key, 900, json.dumps(response_data)) # 15 mins
            except Exception:
                pass
        else:
            _mem_cache[cache_key] = response_data

        return response_data

    except Exception as e:
        logger.error(f"Error fetching dashboard summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while fetching dashboard data.")
