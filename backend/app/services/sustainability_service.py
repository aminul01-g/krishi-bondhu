import os
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.db_models import FarmDiary
from app.models.production_models import SustainabilityMetric

# IPCC Tier 1 approximation coefficients for GHG emissions (kg CO2-eq per unit)
# These are simplified for demonstration but based on general agricultural standards
EMISSION_FACTORS = {
    "synthetic_nitrogen": 5.8,  # kg CO2-eq per kg of N
    "diesel_fuel": 2.68,       # kg CO2-eq per liter
    "electricity": 0.45,       # kg CO2-eq per kWh
}

# Sequestration factors (kg CO2-eq per bigha per year)
SEQUESTRATION_FACTORS = {
    "no-till": 150.0,
    "cover-cropping": 100.0,
    "organic_compost": 80.0,
    "agroforestry": 300.0,
}

async def calculate_carbon_footprint(db: AsyncSession, user_id: str) -> Dict[str, Any]:
    """
    Estimates the farm's carbon footprint by analyzing the FarmDiary for inputs.
    Formula: Sum(Input_Amount * Emission_Factor)
    """
    total_emissions = 0.0

    # Query diary for inputs that contribute to emissions
    stmt = select(FarmDiary).where(
        FarmDiary.user_id == user_id,
        FarmDiary.entry_type == 'expense'
    )
    result = await db.execute(stmt)
    entries = result.scalars().all()

    for entry in entries:
        notes = (entry.notes or "").lower()
        category = (entry.category or "").lower()
        amount = entry.amount

        if "nitrogen" in notes or "urea" in notes or category == "fertilizer":
            # Assuming amount is in kg for urea
            total_emissions += amount * EMISSION_FACTORS["synthetic_nitrogen"]
        elif "diesel" in notes or "fuel" in notes:
            total_emissions += amount * EMISSION_FACTORS["diesel_fuel"]

    return {
        "total_emissions_kg": round(total_emissions, 2),
        "unit": "kg CO2-eq"
    }

async def verify_sustainable_practices(db: AsyncSession, user_id: str) -> List[str]:
    """
    Rule-based engine that scans the FarmDiary for sustainable agriculture practices.
    """
    verified = []

    # Keywords associated with sustainable practices
    practice_map = {
        "no-till": ["no till", "zero tillage", "no-plough"],
        "cover-cropping": ["cover crop", "green manure", "intercropping"],
        "organic_compost": ["compost", "vermicompost", "organic manure"],
        "agroforestry": ["tree planting", "boundary trees", "fruit trees"],
    }

    stmt = select(FarmDiary).where(FarmDiary.user_id == user_id)
    result = await db.execute(stmt)
    entries = result.scalars().all()

    # Flatten all notes into one searchable text
    all_notes = " ".join([e.notes for e in entries if e.notes]).lower()

    for practice, keywords in practice_map.items():
        if any(kw in all_notes for kw in keywords):
            verified.append(practice)

    return verified

async def get_sustainability_scorecard(db: AsyncSession, user_id: str) -> Dict[str, Any]:
    """
    Synthesizes emissions and practices into a final Sustainability Score.
    """
    emissions_data = await calculate_carbon_footprint(db, user_id)
    practices = await verify_sustainable_practices(db, user_id)

    # Calculate Sequestration
    total_offset = sum([SEQUESTRATION_FACTORS.get(p, 0) for p in practices])

    # Calculate Final Score (0-100)
    # Base score starts at 50. Increases with practices, decreases with emissions.
    base_score = 50.0
    practice_bonus = len(practices) * 10.0
    emission_penalty = min(20.0, emissions_data["total_emissions_kg"] / 500.0)

    final_score = max(0, min(100, base_score + practice_bonus - emission_penalty))

    # Persist to DB
    metric = SustainabilityMetric(
        user_id=user_id,
        carbon_score=final_score,
        co2_offset_kg=total_offset,
        verified_practices=practices
    )

    # Update existing or create new
    from sqlalchemy import update
    from app.models.production_models import SustainabilityMetric as SMetric

    existing_stmt = select(SMetric).where(SMetric.user_id == user_id)
    existing_result = await db.execute(existing_stmt)
    existing = existing_result.scalars().first()

    if existing:
        existing.carbon_score = final_score
        existing.co2_offset_kg = total_offset
        existing.verified_practices = practices
    else:
        db.add(metric)

    await db.commit()

    return {
        "score": round(final_score, 1),
        "co2_offset_kg": round(total_offset, 2),
        "verified_practices": practices,
        "grade": "A" if final_score > 80 else "B" if final_score > 60 else "C",
        "recommendation": "Try adding cover crops to increase your carbon offset." if len(practices) < 2 else "Excellent sustainable management!"
    }

async def get_carbon_market_opportunities(score: float, location: str) -> List[Dict[str, Any]]:
    """
    Matches the farmer's score to potential carbon credit schemes.
    """
    opportunities = [
        {"name": "Bangladesh Green Fund", "min_score": 60, "benefit": "Cash subsidy per bigha", "type": "Government"},
        {"name": "Global Carbon Credit Exchange", "min_score": 80, "benefit": "Carbon credits in USD", "type": "International"},
        {"name": "Eco-Agro Partnership", "min_score": 40, "benefit": "Reduced interest on loans", "type": "Private"},
    ]

    matches = [
        opt for opt in opportunities
        if score >= opt["min_score"]
    ]

    return matches
