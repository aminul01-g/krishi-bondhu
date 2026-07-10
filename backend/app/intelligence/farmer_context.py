"""FarmerContextAssembler — turns a user_id + GPS into a rich, structured
context block that is injected into every intelligence query.

This is the missing link the old chat never had: the prior `get_farmer_context`
helper existed but was only used to label a district in the community feed.
Here we assemble profile + GPS + active crops + recent diary + extracted memory
facts + current growing season into one object the agents and tools consume.
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import FarmerProfile, FarmDiary, KnowledgeFact
from app.intelligence.schemas import FarmerContext

# Bangladesh cropping seasons (rough, calendar-based; refined by GPS later).
_SEASON_BY_MONTH = {
    1: "Rabi (Winter)", 2: "Rabi (Winter)", 3: "Rabi (Winter)",
    4: "Kharif-I (Summer)", 5: "Kharif-I (Summer)", 6: "Kharif-I (Summer)",
    7: "Kharif-II (Monsoon)", 8: "Kharif-II (Monsoon)", 9: "Kharif-II (Monsoon)",
    10: "Kharif-II / Post-monsoon", 11: "Rabi (Winter)", 12: "Rabi (Winter)",
}


class FarmerContextAssembler:
    @staticmethod
    def _season(now: Optional[datetime] = None) -> str:
        now = now or datetime.now()
        return _SEASON_BY_MONTH.get(now.month, "Unknown")

    @staticmethod
    async def assemble(
        db: AsyncSession,
        user_id: int,
        external_id: str,
        gps: Optional[Dict[str, float]] = None,
        now: Optional[datetime] = None,
    ) -> FarmerContext:
        """Build a structured FarmerContext from the DB + request GPS."""
        now = now or datetime.now()

        # --- Profile ---
        profile: Optional[FarmerProfile] = None
        try:
            res = await db.execute(
                select(FarmerProfile).where(FarmerProfile.user_id == user_id)
            )
            profile = res.scalars().first()
        except Exception:
            profile = None

        district = profile.district if profile else None
        upazila = profile.upazila if profile else None
        crops = list(profile.crops or []) if profile and profile.crops else []
        land = profile.land_area_bigha if profile else None
        experience = profile.farming_experience_years if profile else None
        phone = profile.phone_number if profile else None

        # --- Recent diary (last 10 entries) ---
        recent_diary: List[Dict[str, Any]] = []
        try:
            dres = await db.execute(
                select(FarmDiary)
                .where(FarmDiary.user_id == external_id)
                .order_by(desc(FarmDiary.date))
                .limit(10)
            )
            for e in dres.scalars().all():
                recent_diary.append(
                    {
                        "date": e.date.isoformat() if e.date else None,
                        "type": e.entry_type,
                        "category": e.category,
                        "crop": e.crop,
                        "amount": e.amount,
                        "unit": e.unit,
                        "notes": e.notes,
                    }
                )
        except Exception:
            recent_diary = []

        # --- Extracted memory facts (cross-conversation) ---
        memory_facts: List[Dict[str, Any]] = []
        try:
            fres = await db.execute(
                select(KnowledgeFact).where(KnowledgeFact.user_id == external_id)
            )
            for f in fres.scalars().all():
                memory_facts.append(
                    {
                        "key": f.fact_key,
                        "value": f.fact_value,
                        "confidence": f.confidence,
                    }
                )
        except Exception:
            memory_facts = []

        season = FarmerContextAssembler._season(now)

        # --- Formatted string for direct injection into prompts ---
        parts: List[str] = []
        if district:
            parts.append(f"District={district}")
        if upazila:
            parts.append(f"Upazila={upazila}")
        if crops:
            parts.append(f"Crops=[{', '.join(crops)}]")
        if land is not None:
            parts.append(f"Land={land} bigha")
        if experience is not None:
            parts.append(f"Experience={experience} years")
        if gps and gps.get("lat") is not None:
            parts.append(f"GPS=({gps['lat']:.3f}, {gps.get('lon', 0):.3f})")
        parts.append(f"Season={season}")
        if memory_facts:
            facts_str = "; ".join(f"{f['key']}={f['value']}" for f in memory_facts[:12])
            parts.append(f"Known facts={facts_str}")
        if recent_diary:
            diary_str = "; ".join(
                f"{d.get('type')}:{d.get('category') or d.get('crop') or '—'}"
                for d in recent_diary[:5]
            )
            parts.append(f"Recent diary={diary_str}")

        formatted = "Farmer context: " + ", ".join(parts) if parts else ""

        return FarmerContext(
            district=district,
            upazila=upazila,
            crops=crops,
            land_area_bigha=land,
            experience_years=experience,
            phone=phone,
            gps=gps,
            season=season,
            recent_diary=recent_diary,
            memory_facts=memory_facts,
            formatted=formatted,
        )
