"""Recommendation service (Phase 2 — Domain depth).

Replaces the soil+irrigation-only crew call with a *reasoning layer* that fuses
signals from soil, irrigation, weather, water balance, pest risk, diary, and
market into prioritized, explainable, dated advisories — each carrying the
signal it came from.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import SoilTestLog, IrrigationLog, KnowledgeFact, FarmDiary

logger = logging.getLogger("RecommendationService")


def _advisory(priority: int, title: str, detail: str, reason: str, source: str, due: str = "") -> Dict[str, Any]:
    return {"priority": priority, "title": title, "detail": detail,
            "reason": reason, "source": source, "due": due}


class RecommendationService:
    @staticmethod
    async def get_personalized_recommendations(
        db: AsyncSession,
        user_id: str,
        gps: Optional[Dict[str, float]] = None,
        language: str = "bn",
    ) -> Dict[str, Any]:
        """
        Fuses multiple domain signals into a prioritized, explainable advisory list.
        """
        advisories: List[Dict[str, Any]] = []

        # --- Context gathering ---
        soil = (await db.execute(
            select(SoilTestLog).where(SoilTestLog.user_id == user_id)
            .order_by(SoilTestLog.timestamp.desc()).limit(1)
        )).scalars().first()

        irr = (await db.execute(
            select(IrrigationLog).where(IrrigationLog.user_id == user_id)
            .order_by(IrrigationLog.timestamp.desc()).limit(1)
        )).scalars().first()

        crop_fact = (await db.execute(
            select(KnowledgeFact).where(KnowledgeFact.user_id == user_id,
                                       KnowledgeFact.fact_key == "crop_planted")
        )).scalars().first()
        crop = (crop_fact.fact_value if crop_fact else "rice") or "rice"

        diary = (await db.execute(
            select(FarmDiary).where(FarmDiary.user_id == user_id)
            .order_by(FarmDiary.date.desc()).limit(5)
        )).scalars().all()

        weather = water = pest_risks = market = None
        if gps and gps.get("lat") is not None:
            try:
                from app.services.weather_service import WeatherService
                from app.services.agronomy_service import AgronomyService
                from app.services.market_service import MarketService

                wsvc = WeatherService()
                weather = await wsvc.get_weather_data(gps["lat"], gps["lon"])
                water = await wsvc.calculate_water_balance(crop, gps["lat"], gps["lon"])
                pest_risks = AgronomyService.evaluate_risk({
                    "temp": weather.get("temp_mean", 30),
                    "humidity": weather.get("humidity", 80),
                    "moisture": (water.get("moisture_index") * 100 if water else None),
                    "leaf_wetness_hours": 4.0,
                })
                msvc = MarketService()
                market = await msvc.get_current_prices(crop, gps["lat"], gps["lon"])
            except Exception as e:  # pragma: no cover - defensive
                logger.warning("Signal enrichment failed", error=str(e))

        # --- Soil advisory ---
        ph = getattr(soil, "derived_ph", None) if soil else None
        if ph is not None:
            try:
                ph_v = float(ph)
                if ph_v < 5.5:
                    advisories.append(_advisory(
                        2, "Correct soil acidity",
                        "Apply agricultural lime; target pH 6.0–6.8 for better nutrient uptake.",
                        f"Latest soil pH is {ph_v:.1f} (acidic).", "soil_test"))
                elif ph_v > 7.5:
                    advisories.append(_advisory(
                        3, "Manage alkaline soil",
                        "Use gypsum and organic matter; avoid excess urea on alkaline soils.",
                        f"Latest soil pH is {ph_v:.1f} (alkaline).", "soil_test"))
            except (TypeError, ValueError):
                pass

        # --- Irrigation / water balance advisory ---
        if water is not None:
            status = water.get("status")
            if status == "Deficit" or (water.get("moisture_index") or 1) < 0.5:
                advisories.append(_advisory(
                    1, "Irrigate soon",
                    f"Soil depletion is high (moisture index {water.get('moisture_index')}). "
                    f"Apply ~{water.get('irrigation_recommendation_mm')} mm.",
                    "Water-balance model shows deficit vs management threshold.",
                    "water_balance", "next 2 days"))
            elif status == "Saturated":
                advisories.append(_advisory(
                    3, "Hold irrigation",
                    "Soil is near saturation; pause irrigation to avoid waterlogging.",
                    "Water-balance model shows saturated soil.", "water_balance"))
        elif irr is not None:
            mi = getattr(irr, "soil_moisture_index", None)
            if mi is not None and float(mi) < 0.4:
                advisories.append(_advisory(
                    1, "Irrigate soon",
                    f"Recent moisture index {mi} is low.",
                    "Latest irrigation log shows dry soil.", "irrigation_log", "next 2 days"))

        # --- Pest / disease advisory ---
        if pest_risks:
            for r in pest_risks:
                if r["level"] == "High":
                    advisories.append(_advisory(
                        1, f"Scout for {r['factor']}",
                        r["recommendation"],
                        f"{r['type']} risk High (p={r['probability']:.2f}); triggers: "
                        f"{', '.join(r['triggers'])}.",
                        "pest_risk_model", "this week"))

        # --- Market advisory (sell/hold) ---
        if market is not None:
            trend = market.get("price_forecast")
            if trend:
                last = trend[-1]
                predicted = last.get("high", last.get("price"))
                current = market.get("current_price")
                if predicted and current and predicted > current * 1.05:
                    advisories.append(_advisory(
                        2, "Consider holding produce",
                        f"Forecast suggests prices may rise (~{predicted} vs {current} BDT/kg). "
                        f"Store if safe; sell if spoilage risk is high.",
                        "Market forecast trending up.", "market_forecast"))
                elif predicted and current and predicted < current * 0.97:
                    advisories.append(_advisory(
                        2, "Consider selling",
                        f"Forecast suggests prices may soften (~{predicted} vs {current} BDT/kg). "
                        f"Prefer selling soon unless storage is cheap.",
                        "Market forecast trending down.", "market_forecast"))

        # --- Diary nudge ---
        if not diary:
            advisories.append(_advisory(
                4, "Keep farm records",
                "Log expenses, inputs, and yields weekly — it improves credit scores and advice.",
                "No recent diary entries found.", "diary"))

        advisories.sort(key=lambda a: a["priority"])

        # --- Narrative (deterministic; LLM optional) ---
        if advisories:
            lines = [f"• {a['title']}: {a['detail']}" for a in advisories[:4]]
            narrative = "\n".join(lines)
        else:
            narrative = "No urgent actions — your farm signals look healthy. Keep monitoring."
        narrative = _maybe_localize(narrative, language)

        data_snapshot = {
            "crop": crop,
            "soil_ph": ph,
            "water_status": water.get("status") if water else None,
            "pest_high": any(r["level"] == "High" for r in (pest_risks or [])),
            "market_trend_up": bool(market and market.get("price_forecast")
                                    and market["price_forecast"][-1].get("high", 0)
                                    > (market.get("current_price") or 0) * 1.05),
        }

        return {
            "advisories": advisories,
            "personalized_advice": narrative,
            "supporting_tips": [a["detail"] for a in advisories],
            "data_snapshot": data_snapshot,
        }


def _maybe_localize(text: str, language: str) -> str:
    """Hook for future localization; passes English text through for now."""
    return text
