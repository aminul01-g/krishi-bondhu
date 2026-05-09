import os
import json
import logging
import httpx
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

logger = logging.getLogger("WeatherService")

# ---------------------------------------------------------------------------
# Generic climate averages for Bangladesh (fallback when NASA POWER is down).
# Source: Bangladesh Meteorological Department long-term normals.
# Keys are 1-indexed month numbers.
# ---------------------------------------------------------------------------
BANGLADESH_CLIMATE_AVERAGES: Dict[int, Dict[str, float]] = {
    1:  {"temp_max": 25.4, "temp_min": 12.7, "temp_mean": 19.1, "humidity": 74.0, "rainfall_mm": 7.0,  "solar_radiation": 13.5},
    2:  {"temp_max": 28.1, "temp_min": 15.5, "temp_mean": 21.8, "humidity": 68.0, "rainfall_mm": 18.0, "solar_radiation": 15.8},
    3:  {"temp_max": 32.5, "temp_min": 20.5, "temp_mean": 26.5, "humidity": 64.0, "rainfall_mm": 35.0, "solar_radiation": 18.2},
    4:  {"temp_max": 33.8, "temp_min": 23.6, "temp_mean": 28.7, "humidity": 71.0, "rainfall_mm": 98.0, "solar_radiation": 18.9},
    5:  {"temp_max": 33.2, "temp_min": 24.5, "temp_mean": 28.9, "humidity": 78.0, "rainfall_mm": 185.0, "solar_radiation": 17.5},
    6:  {"temp_max": 32.1, "temp_min": 25.1, "temp_mean": 28.6, "humidity": 84.0, "rainfall_mm": 310.0, "solar_radiation": 15.0},
    7:  {"temp_max": 31.4, "temp_min": 25.6, "temp_mean": 28.5, "humidity": 86.0, "rainfall_mm": 370.0, "solar_radiation": 13.8},
    8:  {"temp_max": 31.6, "temp_min": 25.8, "temp_mean": 28.7, "humidity": 86.0, "rainfall_mm": 320.0, "solar_radiation": 14.2},
    9:  {"temp_max": 31.6, "temp_min": 25.2, "temp_mean": 28.4, "humidity": 85.0, "rainfall_mm": 250.0, "solar_radiation": 14.8},
    10: {"temp_max": 31.2, "temp_min": 23.4, "temp_mean": 27.3, "humidity": 82.0, "rainfall_mm": 160.0, "solar_radiation": 15.0},
    11: {"temp_max": 29.3, "temp_min": 18.6, "temp_mean": 24.0, "humidity": 78.0, "rainfall_mm": 30.0,  "solar_radiation": 14.0},
    12: {"temp_max": 26.4, "temp_min": 13.9, "temp_mean": 20.2, "humidity": 76.0, "rainfall_mm": 8.0,   "solar_radiation": 13.0},
}

# ---------------------------------------------------------------------------
# Crop parameters for water balance
# ---------------------------------------------------------------------------
CROP_COEFFICIENTS: Dict[str, float] = {
    "rice": 1.20, "paddy": 1.20, "ধান": 1.20,
    "potato": 0.75, "আলু": 0.75,
    "maize": 1.00, "ভুট্টা": 1.00,
    "wheat": 0.85, "গম": 0.85,
    "jute": 1.10, "পাট": 1.10,
    "tomato": 0.90, "টমেটো": 0.90,
    "onion": 0.70, "পেঁয়াজ": 0.70,
    "brinjal": 0.85, "বেগুন": 0.85,
    "default": 0.80,
}

ROOT_DEPTH_MM: Dict[str, float] = {
    "rice": 300, "paddy": 300,
    "potato": 400,
    "maize": 600,
    "wheat": 500,
    "jute": 500,
    "tomato": 500,
    "onion": 300,
    "brinjal": 450,
    "default": 350,
}


class WeatherService:
    """
    Production-grade Service for agricultural weather and irrigation.
    Implements Hargreaves-Samani equation for ET0 and water balance.

    Data source priority:
      1. NASA POWER API  (real satellite + reanalysis data)
      2. Bangladesh climate averages (monthly normals)
    """

    def __init__(self) -> None:
        self.api_key = os.getenv("WEATHER_API_KEY")
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        
        # In a standalone Space environment, skip Redis connection to avoid timeouts and errors
        is_hf_space = os.getenv("SPACE_ID") is not None
        use_redis = os.getenv("USE_REDIS", "false" if is_hf_space else "true").lower() == "true"
        
        self.redis = None
        if use_redis:
            try:
                from redis import Redis
                self.redis: Optional[Any] = Redis.from_url(redis_url, decode_responses=True)
                self.redis.ping()  # Validate connection eagerly
            except Exception as exc:
                logger.warning(f"Redis unavailable ({exc}). Using in-memory cache fallback.")
                self.redis = None
        else:
            logger.info("Redis disabled via config. Using in-memory cache fallback.")

        # Simple in-memory dict cache when Redis is absent
        self._mem_cache: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Cache helpers (Redis-first, in-memory fallback)
    # ------------------------------------------------------------------
    def _cache_get(self, key: str) -> Optional[str]:
        if self.redis:
            try:
                return self.redis.get(key)
            except Exception:
                pass
        return self._mem_cache.get(key)

    def _cache_set(self, key: str, value: str, ttl: int = 3600) -> None:
        if self.redis:
            try:
                self.redis.setex(key, ttl, value)
                return
            except Exception:
                pass
        self._mem_cache[key] = value

    # ------------------------------------------------------------------
    # Weather data acquisition
    # ------------------------------------------------------------------
    async def get_weather_data(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Fetches weather data from NASA POWER API with Redis caching.
        Falls back to Bangladesh monthly climate averages if API is unavailable.
        """
        cache_key = f"weather:{round(lat, 2)}:{round(lon, 2)}"
        cached = self._cache_get(cache_key)
        if cached:
            return json.loads(cached)

        # --- Attempt NASA POWER API ---
        data = await self._fetch_nasa_power(lat, lon)

        if data is None:
            # --- Fallback: Bangladesh climate averages ---
            logger.warning("NASA POWER unavailable. Using Bangladesh climate averages.")
            data = self._get_climate_fallback()

        data["timestamp"] = datetime.now().isoformat()
        data["source"] = data.get("source", "climate_average")
        self._cache_set(cache_key, json.dumps(data))
        return data

    async def _fetch_nasa_power(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Fetch last-3-day average weather from NASA POWER AG community endpoint."""
        today = datetime.now()
        # NASA POWER data has ~2 day latency; request 5 days ago to 2 days ago
        end_date = (today - timedelta(days=2)).strftime("%Y%m%d")
        start_date = (today - timedelta(days=5)).strftime("%Y%m%d")

        params = "T2M_MAX,T2M_MIN,T2M,RH2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN"
        url = (
            f"https://power.larc.nasa.gov/api/temporal/daily/point?"
            f"parameters={params}&community=AG"
            f"&longitude={lon}&latitude={lat}"
            f"&start={start_date}&end={end_date}&format=JSON"
        )

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    logger.warning(f"NASA POWER returned HTTP {response.status_code}")
                    return None

                raw = response.json()
                parameters = raw.get("properties", {}).get("parameter", {})

                def _avg(param_dict: Dict[str, float]) -> float:
                    vals = [v for v in param_dict.values() if v != -999]
                    return round(sum(vals) / len(vals), 2) if vals else 0.0

                return {
                    "temp_max": _avg(parameters.get("T2M_MAX", {})),
                    "temp_min": _avg(parameters.get("T2M_MIN", {})),
                    "temp_mean": _avg(parameters.get("T2M", {})),
                    "humidity": _avg(parameters.get("RH2M", {})),
                    "rainfall_mm": _avg(parameters.get("PRECTOTCORR", {})),
                    "solar_radiation": _avg(parameters.get("ALLSKY_SFC_SW_DWN", {})),
                    "source": "nasa_power",
                }
        except Exception as exc:
            logger.warning(f"NASA POWER API call failed: {exc}")
            return None

    @staticmethod
    def _get_climate_fallback() -> Dict[str, Any]:
        """Return Bangladesh monthly climate normals for the current month."""
        month = datetime.now().month
        data = BANGLADESH_CLIMATE_AVERAGES.get(month, BANGLADESH_CLIMATE_AVERAGES[6])
        return {**data, "source": "climate_average"}

    # ------------------------------------------------------------------
    # Hargreaves-Samani ET₀
    # ------------------------------------------------------------------
    def calculate_et0(self, t_max: float, t_min: float, ra: float = 15.0) -> float:
        """
        Implements the Hargreaves-Samani equation for Reference Evapotranspiration (ET0).
        ET0 = 0.0023 × (Tmean + 17.8) × (Tmax − Tmin)^0.5 × Ra

        Parameters
        ----------
        t_max : float  — Daily maximum temperature (°C)
        t_min : float  — Daily minimum temperature (°C)
        ra    : float  — Extraterrestrial radiation (MJ/m²/day). Default 15.0.

        Returns
        -------
        float — Reference evapotranspiration in mm/day.
        """
        if t_max <= t_min:
            logger.warning(f"Tmax ({t_max}) <= Tmin ({t_min}); clamping delta to 1°C.")
            t_max = t_min + 1.0

        t_mean = (t_max + t_min) / 2
        et0 = 0.0023 * (t_mean + 17.8) * ((t_max - t_min) ** 0.5) * ra
        return round(et0, 2)

    # ------------------------------------------------------------------
    # Full soil water balance
    # ------------------------------------------------------------------
    async def calculate_water_balance(
        self,
        crop: str,
        lat: float,
        lon: float,
        previous_depletion_mm: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Calculates soil water balance based on ET₀, rainfall, crop coefficient (Kc),
        and root-zone available water capacity (AWC).

        Soil water balance equation:
            Depletion_new = Depletion_prev + ETc − Rainfall   (clamped to [0, AWC])
            Irrigation needed when Depletion_new > 0.5 × AWC (MAD = 50%)

        Parameters
        ----------
        crop : str — Crop name (English or Bengali).
        lat, lon : float — GPS coordinates.
        previous_depletion_mm : float — Carry-over depletion from previous day (default 0).
        """
        weather = await self.get_weather_data(lat, lon)
        ra = weather.get("solar_radiation", 15.0)
        et0 = self.calculate_et0(weather["temp_max"], weather["temp_min"], ra)

        # Crop coefficient (Kc)
        crop_key = crop.lower().strip()
        kc = CROP_COEFFICIENTS.get(crop_key, CROP_COEFFICIENTS["default"])
        crop_et = round(et0 * kc, 2)  # ETc (mm/day)

        # Root depth → Available Water Capacity (AWC)
        root_depth = ROOT_DEPTH_MM.get(crop_key, ROOT_DEPTH_MM["default"])
        # AWC = root_depth × volumetric fraction of available water (loam ≈ 0.15 mm/mm)
        awc = root_depth * 0.15  # mm

        # Soil water balance
        rainfall = weather["rainfall_mm"]
        new_depletion = previous_depletion_mm + crop_et - rainfall
        new_depletion = max(0.0, min(new_depletion, awc))  # clamp [0, AWC]

        # Management Allowable Depletion (MAD) = 50% of AWC
        mad = awc * 0.50
        irrigation_needed = max(0.0, new_depletion - mad)

        if new_depletion > mad:
            status = "Deficit"
        elif new_depletion < awc * 0.1:
            status = "Saturated"
        else:
            status = "Sufficient"

        return {
            "et0_mm_day": et0,
            "crop_coefficient_kc": kc,
            "crop_evapotranspiration_mm": crop_et,
            "rainfall_mm": round(rainfall, 2),
            "net_water_balance_mm": round(rainfall - crop_et, 2),
            "root_depth_mm": root_depth,
            "available_water_capacity_mm": round(awc, 2),
            "current_depletion_mm": round(new_depletion, 2),
            "management_allowable_depletion_mm": round(mad, 2),
            "status": status,
            "irrigation_recommendation_mm": round(irrigation_needed, 2),
            "weather_context": weather,
        }
