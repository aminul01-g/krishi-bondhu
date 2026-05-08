import os
import random
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.db_models import FarmDiary
from app.models.production_models import SeasonPlan

logger = logging.getLogger("YieldService")

# ---------------------------------------------------------------------------
# ML Model Loading — Random Forest (primary) with hybrid fallback
# ---------------------------------------------------------------------------

_yield_model_bundle: Optional[Dict[str, Any]] = None
_model_load_attempted: bool = False

def _load_yield_model() -> Optional[Dict[str, Any]]:
    """Attempt to load the trained Random Forest model from disk (once)."""
    global _yield_model_bundle, _model_load_attempted
    if _model_load_attempted:
        return _yield_model_bundle
    _model_load_attempted = True

    # Try multiple possible locations
    candidates = [
        Path(__file__).resolve().parent.parent.parent / "models" / "yield_model.pkl",
        Path("models") / "yield_model.pkl",
        Path("backend") / "models" / "yield_model.pkl",
    ]

    for model_path in candidates:
        if model_path.exists():
            try:
                import joblib
                bundle = joblib.load(model_path)
                logger.info(f"Loaded yield model from {model_path}")
                _yield_model_bundle = bundle
                return bundle
            except Exception as e:
                logger.warning(f"Failed to load yield model from {model_path}: {e}")

    logger.warning("No yield_model.pkl found. Will use hybrid simulation fallback.")
    return None


# Configuration for hybrid simulation fallback
MODEL_WEIGHTS = {
    "rice": {"base": 3.5, "ndvi_impact": 0.8, "input_impact": 0.4},
    "wheat": {"base": 2.8, "ndvi_impact": 0.6, "input_impact": 0.3},
    "potato": {"base": 12.0, "ndvi_impact": 1.2, "input_impact": 0.7},
    "mango": {"base": 1.5, "ndvi_impact": 0.5, "input_impact": 0.2},
    "jute": {"base": 2.0, "ndvi_impact": 0.5, "input_impact": 0.3},
}


async def get_satellite_ndvi(lat: float, lon: float, season: str = "current") -> float:
    """
    Fetches the Normalized Difference Vegetation Index (NDVI) for a location.
    NDVI ranges from -1 to 1. 0.6 to 0.9 indicates healthy green vegetation.
    """
    # Integration point for Google Earth Engine (GEE) or Sentinel-Hub
    # For this implementation, we simulate a high-fidelity NDVI value based on coordinates
    # to ensure the ML model has a realistic input.

    # Deterministic mock based on coordinates to ensure consistency for the same plot
    seed = int(abs(lat * 1000) + abs(lon * 1000))
    random.seed(seed)

    # Typical NDVI for agricultural land in Bangladesh ranges from 0.3 to 0.85
    return random.uniform(0.3, 0.85)


async def _get_weather_features(lat: float, lon: float) -> Dict[str, float]:
    """Fetch weather features for yield prediction from WeatherService."""
    try:
        from app.services.weather_service import WeatherService
        svc = WeatherService()
        weather = await svc.get_weather_data(lat, lon)
        return {
            "rainfall_mm": weather.get("rainfall_mm", 500.0) * 30,  # Scale daily to monthly approx
            "temp_mean": weather.get("temp_mean", 28.0),
            "humidity": weather.get("humidity", 75.0),
        }
    except Exception as e:
        logger.warning(f"Weather fetch for yield failed: {e}. Using defaults.")
        return {"rainfall_mm": 800.0, "temp_mean": 28.0, "humidity": 75.0}


async def predict_yield(
    db: AsyncSession, user_id: str, crop: str, lat: float, lon: float
) -> Dict[str, Any]:
    """
    Predicts the yield for the upcoming season.

    Primary path: Trained Random Forest model (loaded from yield_model.pkl).
    Fallback path: Hybrid simulation (Base + NDVI + History + Noise).
    """
    # 1. Get Satellite Health Index
    ndvi = await get_satellite_ndvi(lat, lon)

    # 2. Analyze Historical Performance from Farm Diary
    stmt = select(FarmDiary).where(
        FarmDiary.user_id == user_id,
        FarmDiary.crop == crop,
        FarmDiary.entry_type == 'yield'
    ).order_by(FarmDiary.date.desc()).limit(3)

    result = await db.execute(stmt)
    history = result.scalars().all()
    avg_historical_yield = float(np.mean([h.amount for h in history])) if history else 0.0

    # 3. Try ML model (primary)
    bundle = _load_yield_model()
    prediction_source = "hybrid_simulation"

    if bundle:
        try:
            model = bundle["model"]
            le = bundle["label_encoder"]
            crop_lower = crop.lower().strip()

            # Encode crop (handle unseen crops gracefully)
            if crop_lower in le.classes_:
                crop_encoded = le.transform([crop_lower])[0]
            else:
                crop_encoded = le.transform(["rice"])[0]  # default to rice
                logger.info(f"Crop '{crop}' not in model classes. Defaulting to 'rice'.")

            # Get weather features
            weather_feats = await _get_weather_features(lat, lon)

            # Build feature vector: [crop_encoded, ndvi, rainfall_mm, temp_mean,
            #                         humidity, historical_avg_yield, input_cost_normalized]
            features = np.array([[
                crop_encoded,
                ndvi,
                weather_feats["rainfall_mm"],
                weather_feats["temp_mean"],
                weather_feats["humidity"],
                avg_historical_yield if avg_historical_yield > 0 else 3.0,
                0.5,  # Default normalized input cost
            ]])

            predicted_val = float(model.predict(features)[0])
            predicted_val = max(0.1, predicted_val)
            confidence = 0.80 if not history else min(0.95, 0.80 + (len(history) * 0.05))
            prediction_source = "random_forest"
            logger.info(f"Yield prediction via Random Forest: {predicted_val:.2f} t/bigha")

        except Exception as e:
            logger.warning(f"RF model prediction failed: {e}. Falling back to simulation.")
            bundle = None  # Force fallback

    # 4. Fallback: Hybrid simulation
    if not bundle:
        crop_params = MODEL_WEIGHTS.get(crop.lower(), MODEL_WEIGHTS["rice"])
        predicted_val = crop_params["base"] + (ndvi * crop_params["ndvi_impact"] * 2)

        if avg_historical_yield > 0:
            predicted_val = (predicted_val * 0.7) + (avg_historical_yield * 0.3)

        noise = random.uniform(-0.2, 0.2)
        predicted_val = max(0.1, predicted_val + noise)
        confidence = 0.6 if not history else min(0.95, 0.6 + (len(history) * 0.1))

    return {
        "predicted_yield": round(predicted_val, 2),
        "unit": "tons/bigha",
        "ndvi": round(ndvi, 3),
        "confidence": round(confidence, 2),
        "historical_avg": round(avg_historical_yield, 2),
        "prediction_source": prediction_source,
    }


async def generate_season_plan(
    db: AsyncSession, user_id: str, crop: str, lat: float, lon: float
) -> Dict[str, Any]:
    """
    Synthesizes the yield prediction into a comprehensive seasonal roadmap.
    This is the input that the YieldPlanner agent will use to generate the final Bengali response.
    """
    prediction = await predict_yield(db, user_id, crop, lat, lon)

    # Logic for planting window based on crop type and regional typicals
    # In a full system, this would query a CropCalendar service
    planting_window = "Mid-June to Early July" if crop.lower() == "rice" else "November to December"

    # Generate a structured plan
    plan = {
        "prediction": prediction,
        "roadmap": [
            {"phase": "Preparation", "action": "Soil testing and land leveling", "timing": "2 weeks before planting"},
            {"phase": "Planting", "action": f"Sow {crop} seeds during the {planting_window} window", "timing": "Start of Season"},
            {"phase": "Nutrition", "action": "First dose of Nitrogen-rich fertilizer", "timing": "Week 3"},
            {"phase": "Monitoring", "action": "Check for stem borer and leaf fold pests", "timing": "Week 6-8"},
            {"phase": "Harvest", "action": "Harvest when grains reach 80% maturity", "timing": "End of Season"}
        ],
        "risk_factors": ["Excessive rainfall during flowering", "Potential for brown planthopper infestation"]
    }

    # Persist the plan to the DB
    new_plan = SeasonPlan(
        user_id=user_id,
        crop=crop,
        season_year=datetime.now().year,
        predicted_yield=prediction["predicted_yield"],
        confidence_score=prediction["confidence"],
        plan_details=plan
    )
    db.add(new_plan)
    await db.commit()
    await db.refresh(new_plan)

    return {
        "plan_id": new_plan.id,
        "details": plan
    }
