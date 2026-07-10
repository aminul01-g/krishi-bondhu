"""Agronomy service (Phase 1 — Data realism).

Replaces the day-bucket growth-stage heuristic and the hardcoded
`if district == "Pabna": locust` risk rule with:
  * GDD-accumulation phenology against crop-specific curves.
  * A probability-based risk scorer (disease / drought / pest) that returns a
    level, a probability, the triggering conditions, and a recommendation.
"""
from __future__ import annotations

import math
from datetime import datetime, date
from typing import Dict, List, Optional, Sequence, Tuple

# Crop-specific phenology as cumulative GDD thresholds (°C-days, base 10°C).
# Each entry: (stage_name, gdd_at_stage_start).
PHENOLOGY: Dict[str, List[Tuple[str, int]]] = {
    "rice": [
        ("Germination", 0), ("Seedling/Tillering", 200), ("Stem Elongation", 600),
        ("Panicle Initiation", 1000), ("Flowering/Heading", 1350), ("Ripening/Harvest", 1750),
    ],
    "wheat": [
        ("Germination", 0), ("Tillering", 150), ("Stem Elongation", 500),
        ("Booting", 900), ("Heading", 1200), ("Ripening/Harvest", 1600),
    ],
    "maize": [
        ("Germination", 0), ("Seedling", 120), ("Vegetative", 450),
        ("Tasseling", 850), ("Silking", 1100), ("Grain-fill/Ripening", 1500),
    ],
}
DEFAULT_PHENOLOGY = [
    ("Germination", 0), ("Vegetative", 200), ("Stem Elongation", 600),
    ("Reproductive", 1000), ("Maturity", 1500), ("Ripening/Harvest", 1800),
]

CROP_KEYS = {
    "rice": "rice", "ধান": "rice", "paddy": "rice",
    "wheat": "wheat", "গম": "wheat",
    "maize": "maize", "ভুট্টা": "maize", "corn": "maize",
}

# Seasonal pest-pressure prior by month (0..1), generic for Bangladesh.
PEST_SEASON_PRIOR = {3: 0.5, 4: 0.7, 5: 0.6, 6: 0.4, 9: 0.5, 10: 0.6}


class AgronomyService:
    BASE_TEMP = 10.0

    @staticmethod
    def calculate_gdd(base_temp: float, min_temp: float, max_temp: float) -> float:
        """Growing Degree Days for a single day."""
        avg_temp = (max_temp + min_temp) / 2
        return max(avg_temp - base_temp, 0)

    @classmethod
    def accumulate_gdd(
        cls,
        history_temps: Sequence[Dict[str, float]],
        base_temp: Optional[float] = None,
    ) -> float:
        """Sum GDD over a list of daily {min, max} (or {tmin, tmax}) records."""
        base_temp = base_temp if base_temp is not None else cls.BASE_TEMP
        total = 0.0
        for rec in history_temps or []:
            tmin = rec.get("min", rec.get("tmin", 0))
            tmax = rec.get("max", rec.get("tmax", 0))
            total += cls.calculate_gdd(base_temp, tmin, tmax)
        return round(total, 1)

    @staticmethod
    def _phenology_for(crop: str) -> List[Tuple[str, int]]:
        key = CROP_KEYS.get(crop.lower().strip(), "default")
        return PHENOLOGY.get(key, DEFAULT_PHENOLOGY)

    @classmethod
    def predict_growth_stage(
        cls,
        crop_name: str,
        planting_date: Optional[date],
        history_temps: Sequence[Dict[str, float]],
        as_of: Optional[date] = None,
    ) -> Dict[str, object]:
        """
        Predicts growth stage from accumulated GDD vs the crop phenology curve.

        If `planting_date` is given but no `history_temps`, GDD is approximated
        from days-since-planting at a rough average rate (clearly a fallback).
        """
        as_of = as_of or date.today()
        stages = cls._phenology_for(crop_name)

        if planting_date:
            days_since = (as_of - planting_date).days
        else:
            days_since = None

        if history_temps:
            gdd = cls.accumulate_gdd(history_temps)
        elif planting_date and days_since is not None:
            # Fallback: ~18 GDD/day average for warm-season crops in BD.
            gdd = round(max(days_since, 0) * 18.0, 1)
        else:
            return {
                "crop": crop_name,
                "stage": "Unknown (no planting date or temperature history)",
                "cumulative_gdd": 0.0,
                "next_stage": stages[1][0] if len(stages) > 1 else None,
                "progress_to_next": 0.0,
                "days_since_planting": days_since,
            }

        # Find current stage and progress toward the next.
        current_stage = stages[0][0]
        next_stage = None
        progress = 0.0
        for i, (name, thr) in enumerate(stages):
            if gdd >= thr:
                current_stage = name
                if i + 1 < len(stages):
                    nxt_name, nxt_thr = stages[i + 1]
                    next_stage = nxt_name
                    span = nxt_thr - thr
                    progress = min(1.0, (gdd - thr) / span) if span > 0 else 1.0
                else:
                    next_stage = None
                    progress = 1.0
            else:
                if next_stage is None:
                    next_stage = name
                break

        return {
            "crop": crop_name,
            "stage": current_stage,
            "cumulative_gdd": gdd,
            "next_stage": next_stage,
            "progress_to_next": round(progress, 3),
            "days_since_planting": days_since,
        }

    @staticmethod
    def _level_from_probability(p: float) -> str:
        if p >= 0.4:
            return "High"
        if p >= 0.3:
            return "Moderate"
        return "Low"

    @classmethod
    def evaluate_risk(
        cls,
        current_conditions: Dict[str, float],
        historical_facts: Optional[Sequence] = None,
        as_of: Optional[date] = None,
    ) -> List[Dict[str, object]]:
        """
        Probability-based multi-risk assessment. No hardcoded district logic —
        pest risk comes from a seasonal prior + conditions and is extensible via
        a regional alert feed.
        """
        as_of = as_of or date.today()
        temp = float(current_conditions.get("temp", 30))
        humidity = float(current_conditions.get("humidity", 80))
        moisture = current_conditions.get("moisture", None)
        rainfall = current_conditions.get("rainfall_mm", 0.0)
        leaf_wetness = current_conditions.get("leaf_wetness_hours", 0.0)
        month = as_of.month

        risks: List[Dict[str, object]] = []

        # --- Disease (fungal) pressure ---
        hum_fav = max(0.0, (humidity - 80) / 20.0)
        temp_fav = 1.0 if 22 <= temp <= 32 else max(0.0, 1.0 - abs(temp - 27) / 15.0)
        lw = min(1.0, float(leaf_wetness) / 10.0)
        disease_p = min(1.0, 0.05 + 0.55 * hum_fav * temp_fav + 0.30 * lw)
        triggers = []
        if humidity > 85:
            triggers.append(f"high humidity ({humidity:.0f}%)")
        if 22 <= temp <= 32:
            triggers.append("favorable temperature")
        if leaf_wetness and leaf_wetness > 4:
            triggers.append(f"leaf wetness {leaf_wetness:.0f}h")
        risks.append({
            "type": "Disease",
            "factor": "Fungal Blight",
            "level": cls._level_from_probability(disease_p),
            "probability": round(disease_p, 3),
            "triggers": triggers,
            "recommendation": "Increase scouting; consider need-based fungicide only above threshold."
            if disease_p >= 0.3 else "Monitor; conditions mildly favorable.",
        })

        # --- Drought / water stress ---
        if moisture is not None:
            moisture = float(moisture)
            drought_p = max(0.0, min(1.0, (35.0 - moisture) / 35.0))
            # Recent rainfall reduces drought risk.
            drought_p = max(0.0, drought_p - min(0.5, float(rainfall) / 20.0))
            d_triggers = []
            if moisture < 20:
                d_triggers.append(f"low soil moisture ({moisture:.0f}%)")
            if rainfall and rainfall < 2:
                d_triggers.append("little recent rainfall")
            risks.append({
                "type": "Environmental",
                "factor": "Drought Stress",
                "level": cls._level_from_probability(drought_p),
                "probability": round(drought_p, 3),
                "triggers": d_triggers,
                "recommendation": "Schedule irrigation; soil depletion approaching management threshold."
                if drought_p >= 0.3 else "Adequate soil moisture.",
            })

        # --- Pest pressure (seasonal prior + conditions) ---
        pest_prior = PEST_SEASON_PRIOR.get(month, 0.3)
        temp_pest = max(0.0, (temp - 28) / 8.0)
        pest_p = min(1.0, 0.1 + 0.4 * temp_pest + 0.4 * pest_prior)
        p_triggers = []
        if pest_prior >= 0.5:
            p_triggers.append(f"seasonal pest pressure (month {month})")
        if temp >= 30:
            p_triggers.append(f"warm temperature ({temp:.0f}°C)")
        risks.append({
            "type": "Pest",
            "factor": "Seasonal Pest Pressure",
            "level": cls._level_from_probability(pest_p),
            "probability": round(pest_p, 3),
            "triggers": p_triggers,
            "recommendation": "Set pheromone traps; conserve natural enemies; spray only above threshold."
            if pest_p >= 0.3 else "Low pest pressure expected; routine monitoring.",
        })

        return risks
