"""ToolRegistry — the real "tools" the intelligence layer can call.

Each tool wraps a domain service, returns a :class:`ToolTrace` carrying a
short summary plus *provenance* (where the number came from, simulated or not).
This is what makes answers grounded instead of hallucinated, and lets the UI be
honest about data quality.
"""
from __future__ import annotations

from typing import List, Optional

from app.intelligence.schemas import FarmerContext, ToolTrace

# Crop name -> canonical key used by the domain services. Bengali + English.
CROP_ALIASES = {
    "rice": "rice", "ধান": "rice", "paddy": "rice", "চাল": "rice",
    "wheat": "wheat", "গম": "wheat",
    "potato": "potato", "আলু": "potato",
    "mango": "mango", "আম": "mango",
    "jute": "jute", "পাট": "jute",
    "onion": "onion", "পেঁয়াজ": "onion", "peyaj": "onion",
    "tomato": "tomato", "টমেটো": "tomato",
    "brinjal": "brinjal", "বেগুন": "brinjal", "eggplant": "brinjal",
    "chili": "chili", "মরিচ": "chili", "chilli": "chili",
    "maize": "maize", "ভুট্টা": "maize", "corn": "maize",
    "cabbage": "cabbage", "বাঁধাকপি": "cabbage",
}


def detect_crop(text: str) -> Optional[str]:
    low = (text or "").lower()
    for token, canon in CROP_ALIASES.items():
        if token in low:
            return canon
    return None


def _summarize(obj, max_len: int = 320) -> str:
    s = str(obj)
    return s if len(s) <= max_len else s[:max_len] + "…"


async def weather_tool(db, ctx: FarmerContext, message: str,
                       gps: Optional[dict], external_id: str = "") -> ToolTrace:
    if not gps or gps.get("lat") is None:
        return ToolTrace(tool="weather", called=False, error="no_gps")
    try:
        from app.services.weather_service import WeatherService

        svc = WeatherService()
        data = await svc.get_weather_data(gps["lat"], gps["lon"])
        return ToolTrace(
            tool="weather",
            called=True,
            result_summary=_summarize(
                {k: data.get(k) for k in
                 ("temp_mean", "humidity", "rainfall_mm", "source")}
            ),
            provenance={"source": data.get("source"), "simulated": False},
        )
    except Exception as e:  # pragma: no cover - defensive
        return ToolTrace(tool="weather", called=False, error=str(e)[:200])


async def water_balance_tool(db, ctx: FarmerContext, message: str,
                             gps: Optional[dict], external_id: str = "") -> ToolTrace:
    if not gps or gps.get("lat") is None:
        return ToolTrace(tool="water_balance", called=False, error="no_gps")
    crop = detect_crop(message) or (ctx.crops[0] if ctx.crops else "rice")
    try:
        from app.services.weather_service import WeatherService

        svc = WeatherService()
        data = await svc.calculate_water_balance(crop, gps["lat"], gps["lon"])
        return ToolTrace(
            tool="water_balance",
            called=True,
            result_summary=_summarize(
                {k: data.get(k) for k in
                 ("et0_mm_day", "status", "irrigation_recommendation_mm",
                  "moisture_index")}
            ),
            provenance={"crop": crop, "source": data.get("weather_context", {}).get("source")},
        )
    except Exception as e:  # pragma: no cover - defensive
        return ToolTrace(tool="water_balance", called=False, error=str(e)[:200])


async def market_tool(db, ctx: FarmerContext, message: str,
                      gps: Optional[dict], external_id: str = "") -> ToolTrace:
    crop = detect_crop(message) or (ctx.crops[0] if ctx.crops else "rice")
    try:
        from app.services.market_service import MarketService

        svc = MarketService()
        data = await svc.get_current_prices(crop, gps.get("lat") if gps else None,
                                            gps.get("lon") if gps else None)
        simulated = bool(data.get("simulated")) or \
            "simulated" in str(data.get("source", "")).lower()
        return ToolTrace(
            tool="market",
            called=True,
            result_summary=_summarize(
                {k: data.get(k) for k in
                 ("current_price", "predicted_price", "source")}
            ),
            provenance={"crop": crop, "source": data.get("source"),
                        "simulated": simulated},
        )
    except Exception as e:  # pragma: no cover - defensive
        return ToolTrace(tool="market", called=False, error=str(e)[:200])


async def yield_tool(db, ctx: FarmerContext, message: str,
                     gps: Optional[dict], external_id: str = "") -> ToolTrace:
    if not gps or gps.get("lat") is None:
        return ToolTrace(tool="yield", called=False, error="no_gps")
    crop = detect_crop(message) or (ctx.crops[0] if ctx.crops else "rice")
    try:
        from app.services.yield_service import predict_yield

        data = await predict_yield(db, external_id, crop, gps["lat"], gps["lon"])
        simulated = "simulation" in str(data.get("prediction_source", "")).lower() or \
            bool(data.get("ndvi_estimated"))
        return ToolTrace(
            tool="yield",
            called=True,
            result_summary=_summarize(
                {k: data.get(k) for k in
                 ("predicted_yield", "confidence", "prediction_source")}
            ),
            provenance={"crop": crop, "source": data.get("prediction_source"),
                        "simulated": simulated},
        )
    except Exception as e:  # pragma: no cover - defensive
        return ToolTrace(tool="yield", called=False, error=str(e)[:200])


async def diary_search_tool(db, ctx: FarmerContext, message: str,
                            gps: Optional[dict], external_id: str = "") -> ToolTrace:
    try:
        if not ctx.recent_diary:
            return ToolTrace(tool="diary", called=False, error="no_entries")
        return ToolTrace(
            tool="diary",
            called=True,
            result_summary=_summarize(
                f"{len(ctx.recent_diary)} recent entries; "
                f"latest: {ctx.recent_diary[0].get('type')}/"
                f"{ctx.recent_diary[0].get('category') or ctx.recent_diary[0].get('crop')}"
            ),
            provenance={"entries": len(ctx.recent_diary)},
        )
    except Exception as e:  # pragma: no cover - defensive
        return ToolTrace(tool="diary", called=False, error=str(e)[:200])


# Registry: name -> coroutine factory signature (db, ctx, message, gps, user_id_int)
TOOL_REGISTRY = {
    "weather": weather_tool,
    "water_balance": water_balance_tool,
    "market": market_tool,
    "yield": yield_tool,
    "diary": diary_search_tool,
}


async def run_tool(name: str, db, ctx: FarmerContext, message: str,
                   gps: Optional[dict], external_id: str = "") -> ToolTrace:
    fn = TOOL_REGISTRY.get(name)
    if not fn:
        return ToolTrace(tool=name, called=False, error="unknown_tool")
    try:
        return await fn(db, ctx, message, gps, external_id)
    except Exception as e:  # pragma: no cover - defensive
        return ToolTrace(tool=name, called=False, error=str(e)[:200])
