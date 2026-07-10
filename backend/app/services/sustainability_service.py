"""Sustainability / carbon service (Phase 2 — Domain depth).

Replaces substring-matching on free-text notes + a `base-50` score with:
  * Structured parsing of diary input events (type, quantity, unit, confidence).
  * IPCC Tier-1 emission factors applied to parsed quantities (not raw notes).
  * Per-practice sequestration with documented factors + uncertainty.
  * A normalized, monotonic, *explainable* sustainability score.
  * A carbon-market matcher driven by eligibility rules + rationale.
"""
from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional

from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import FarmDiary
from app.models.production_models import SustainabilityMetric

logger = logging.getLogger("SustainabilityService")

# ---------------------------------------------------------------------------
# Emission factors (IPCC Tier-1, simplified, documented). kg CO2-eq per unit.
# ---------------------------------------------------------------------------
EMISSION_FACTORS = {
    "synthetic_nitrogen": 5.8,   # kg CO2-eq per kg of N applied (direct + indirect)
    "diesel_fuel": 2.68,         # kg CO2-eq per litre
    "electricity": 0.46,         # kg CO2-eq per kWh (Bangladesh grid avg)
}

# Nutrient content of common N fertilizers (fraction of active N).
N_CONTENT = {
    "urea": 0.46,
    "dap": 0.18,
    "potash": 0.0,   # potassium — no direct N2O from K
}

# Keyword cues used to classify a diary entry into an input type.
INPUT_TYPES: Dict[str, Dict[str, Any]] = {
    "urea":       {"aliases": ["urea", "ইউরিয়া", "ইউরিয়া", "ইউরিয়া"], "n_content": 0.46},
    "dap":        {"aliases": ["dap", "ডিএপি", "ডাই-অ্যামোনিয়াম", "টিএসপি"], "n_content": 0.18},
    "potash":     {"aliases": ["potash", "পটাশ", "এমওপি", "এমওপি"], "n_content": 0.0},
    "diesel":     {"aliases": ["diesel", "ডিজেল", "ফুয়েল", "জ্বালানি"], "n_content": 0.0},
    "electricity": {"aliases": ["electricity", "বিদ্যুৎ", "ইলেকট্রিক"], "n_content": 0.0},
}

# Sequestration factors (kg CO2-eq per bigha per year) + uncertainty (+/-).
SEQUESTRATION_FACTORS = {
    "no-till": {"value": 150.0, "uncertainty": 40.0},
    "cover-cropping": {"value": 100.0, "uncertainty": 30.0},
    "organic_compost": {"value": 80.0, "uncertainty": 25.0},
    "agroforestry": {"value": 300.0, "uncertainty": 80.0},
    "reduced-nitrogen": {"value": 60.0, "uncertainty": 20.0},
    # Water-efficiency practices (e.g. drip irrigation) are NOT nitrogen
    # reduction — they save irrigation water. Small, documented offset.
    "water_efficiency": {"value": 40.0, "uncertainty": 15.0},
}

# Monetary units. Cost-only diary entries (e.g. 300 BDT "Urea") must NEVER be
# treated as a physical mass/volume — emissions can never be derived from a
# monetary amount. (See #20.)
MONETARY_UNITS = {
    "bdt", "tk", "taka", "rs", "inr", "usd", "$", "rupee", "rupiah", "৳",
    "₹", "টাকা", "রুপি",
}


def _is_monetary_unit(unit: Optional[str]) -> bool:
    return bool(unit) and unit.lower() in MONETARY_UNITS

PRACTICE_KEYWORDS = {
    "no-till": ["no till", "zero tillage", "ন চাষ", "চাষ ছাড়া"],
    "cover-cropping": ["cover crop", "green manure", "intercropping", "সবুজ সার", "আন্তঃচাষ"],
    "organic_compost": ["compost", "vermicompost", "organic manure", "কম্পোস্ট", "জৈব সার"],
    "agroforestry": ["tree planting", "boundary trees", "fruit trees", "বাগান", "গাছ"],
    "reduced-nitrogen": ["reduced nitrogen", "less urea", "কম ইউরিয়া", "সুষম সার"],
    "water_efficiency": ["drip", "drip irrigation", "সেচ ফোয়ারা", "ফোয়ারা সেচ"],
}

# Structured diary `category` / `entry_type` values that map directly to a
# verified practice. When present, this gives high-confidence (0.9) detection
# and we only fall back to fuzzy keyword matching otherwise. (See #23.)
CATEGORY_TO_PRACTICE = {
    "compost": "organic_compost",
    "organic_manure": "organic_compost",
    "vermicompost": "organic_compost",
    "cover_crop": "cover-cropping",
    "green_manure": "cover-cropping",
    "no_till": "no-till",
    "zero_till": "no-till",
    "agroforestry": "agroforestry",
    "tree_planting": "agroforestry",
    "reduced_nitrogen": "reduced-nitrogen",
    "less_urea": "reduced-nitrogen",
    "balanced_fertilizer": "reduced-nitrogen",
    "drip": "water_efficiency",
    "drip_irrigation": "water_efficiency",
    "water_efficiency": "water_efficiency",
}

# Reference annual emissions (kg CO2-eq) used to normalize the penalty.
REFERENCE_EMISSIONS = 400.0


# ---------------------------------------------------------------------------
# Structured input parsing
# ---------------------------------------------------------------------------
def _classify_input(category: Optional[str], notes: Optional[str]) -> Optional[str]:
    text = f"{category or ''} {(notes or '')}".lower()
    for itype, spec in INPUT_TYPES.items():
        if category and category.lower() == itype:
            return itype
        if any(kw in text for kw in spec["aliases"]):
            return itype
    return None


def parse_input_events(entries: List[Any]) -> List[Dict[str, Any]]:
    """Turn raw diary expense entries into structured, auditable input events."""
    events: List[Dict[str, Any]] = []
    for e in entries:
        if getattr(e, "entry_type", None) != "expense":
            continue
        itype = _classify_input(getattr(e, "category", None), getattr(e, "notes", None))
        if not itype:
            continue

        amount = getattr(e, "amount", 0.0) or 0.0
        unit = (getattr(e, "unit", None) or "").lower()
        # Mass/volume units let us compute real emissions; cost-only entries can't.
        known_qty = unit in ("kg", "mon", "l", "liter", "লিটার", "kwh")
        is_cost = _is_monetary_unit(unit)

        ef_key = None
        canonical_qty = amount
        canonical_unit = unit
        confidence = 0.9 if known_qty else 0.4
        # A monetary entry (e.g. 300 BDT "Urea") is a cost, NOT a physical mass.
        # Never derive emissions from a monetary amount — skip the N/EF factors.
        if not is_cost:
            if itype in ("urea", "dap", "potash"):
                ef_key = "synthetic_nitrogen"
                n_content = N_CONTENT.get(itype, 0.0)
                # Emissions are counted on elemental N, not on fertilizer mass.
                canonical_qty = amount * n_content
                canonical_unit = "kg N"
            elif itype == "diesel":
                ef_key = "diesel_fuel"
                canonical_unit = "L"
            elif itype == "electricity":
                ef_key = "electricity"
                canonical_unit = "kWh"
        else:
            # Cost-only: low confidence, no emission factor is applicable.
            confidence = 0.3

        emission_kg = (
            round(canonical_qty * EMISSION_FACTORS[ef_key], 4)
            if ef_key is not None else None
        )
        events.append({
            "type": itype,
            "emission_factor_key": ef_key,
            "quantity": amount,
            "unit": unit,
            "is_cost": is_cost,
            "canonical_quantity": round(canonical_qty, 3),
            "canonical_unit": canonical_unit,
            "emission_kg": emission_kg,
            "confidence": confidence,
            "source": (getattr(e, "notes", None) or getattr(e, "category", None) or ""),
        })
    return events


# ---------------------------------------------------------------------------
# Emissions
# ---------------------------------------------------------------------------
async def calculate_carbon_footprint(db: AsyncSession, user_id: str) -> Dict[str, Any]:
    """Estimates emissions from parsed diary inputs using IPCC factors."""
    stmt = select(FarmDiary).where(
        FarmDiary.user_id == user_id, FarmDiary.entry_type == "expense"
    )
    result = await db.execute(stmt)
    entries = result.scalars().all()

    events = parse_input_events(entries)
    breakdown: List[Dict[str, Any]] = []
    total = 0.0
    for ev in events:
        ef_key = ev["emission_factor_key"]
        if not ef_key:
            continue
        factor = EMISSION_FACTORS[ef_key]
        emission = ev["canonical_quantity"] * factor
        total += emission
        breakdown.append({
            "type": ev["type"],
            "quantity": ev["canonical_quantity"],
            "unit": ev["canonical_unit"],
            "factor": factor,
            "emission_kg": round(emission, 2),
            "confidence": ev["confidence"],
        })

    return {
        "total_emissions_kg": round(total, 2),
        "unit": "kg CO2-eq",
        "breakdown": breakdown,
        "unparsed_cost_entries": sum(1 for e in events if e["emission_factor_key"] is None),
    }


# ---------------------------------------------------------------------------
# Practices
# ---------------------------------------------------------------------------
async def verify_sustainable_practices(db: AsyncSession, user_id: str) -> List[Dict[str, Any]]:
    """Rule-based engine that detects sustainable practices with confidence.

    Detection prefers structured diary ``category``/``entry_type`` (high,
    category-certain confidence) and only falls back to fuzzy keyword matching
    on free-text notes (capped confidence reflecting the weaker signal). (#23)
    """
    stmt = select(FarmDiary).where(FarmDiary.user_id == user_id)
    result = await db.execute(stmt)
    entries = result.scalars().all()

    # practice -> (confidence, evidence)
    found: Dict[str, Any] = {}

    def _record(practice: str, confidence: float, evidence: List[str]) -> None:
        cur = found.get(practice, {"confidence": 0.0, "evidence": []})
        cur["confidence"] = max(cur["confidence"], confidence)
        for ev in evidence:
            if ev not in cur["evidence"]:
                cur["evidence"].append(ev)
        found[practice] = cur

    for e in entries:
        cat = (getattr(e, "category", None) or "").lower().strip()
        notes = (getattr(e, "notes", None) or "").lower()

        # 1) Structured category match — strongest, category-certain signal.
        structured = CATEGORY_TO_PRACTICE.get(cat)
        if structured:
            _record(structured, 0.9, [f"category:{cat}"])

        # 2) Keyword fallback on free-text notes (capped below category certainty).
        for practice, keywords in PRACTICE_KEYWORDS.items():
            hits = [kw for kw in keywords if kw in notes]
            if hits:
                # More distinct cues -> higher confidence, but capped at 0.8 so a
                # structured category always outranks fuzzy text.
                conf = min(0.8, 0.5 + 0.25 * len(hits))
                _record(practice, conf, hits)

    verified = [
        {"practice": p, "confidence": round(v["confidence"], 2), "evidence": v["evidence"]}
        for p, v in found.items()
    ]
    return verified


# ---------------------------------------------------------------------------
# Scorecard
# ---------------------------------------------------------------------------
async def get_sustainability_scorecard(db: AsyncSession, user_id: str) -> Dict[str, Any]:
    """Synthesizes emissions, practices, and sequestration into an explainable score."""
    emissions_data = await calculate_carbon_footprint(db, user_id)
    practices = await verify_sustainable_practices(db, user_id)

    total_emissions = emissions_data["total_emissions_kg"]

    # Sequestration from verified practices (weighted by confidence).
    seq_components = []
    total_offset = 0.0
    for p in practices:
        spec = SEQUESTRATION_FACTORS.get(p["practice"])
        if not spec:
            continue
        contrib = spec["value"] * p["confidence"]
        total_offset += contrib
        seq_components.append({
            "practice": p["practice"],
            "co2_offset_kg": round(contrib, 2),
            "confidence": p["confidence"],
        })

    # Explainable, monotonic score.
    practice_bonus = 0.0
    for p in practices:
        spec = SEQUESTRATION_FACTORS.get(p["practice"])
        if spec and p["confidence"] > 0.5:
            practice_bonus += spec["value"] * 0.05
    practice_bonus = min(40.0, practice_bonus)
    emission_penalty = min(30.0, total_emissions / REFERENCE_EMISSIONS * 30.0)
    # Calibration: the score is anchored at 0 (not 50). A farmer with no diary
    # data / no verified practices / no emissions scores ~0 ("C" band), so the
    # number honestly reflects lack of evidence rather than implying a middling
    # baseline. The floor therefore derives from verified practices + penalties.
    base_score = 0.0
    final_score = max(0.0, min(100.0, base_score + practice_bonus - emission_penalty))
    net_kg = round(total_offset - total_emissions, 2)

    grade = "A" if final_score > 80 else "B" if final_score > 60 else "C"
    recommendation = (
        "Try adding cover crops or compost to increase your carbon offset."
        if len(practices) < 2
        else "Excellent sustainable management!"
    )

    # Persist
    metric = SustainabilityMetric(
        user_id=user_id, carbon_score=final_score, co2_offset_kg=round(total_offset, 2),
        verified_practices=[p["practice"] for p in practices],
    )
    existing_stmt = select(SustainabilityMetric).where(SustainabilityMetric.user_id == user_id)
    existing = (await db.execute(existing_stmt)).scalars().first()
    if existing:
        existing.carbon_score = final_score
        existing.co2_offset_kg = round(total_offset, 2)
        existing.verified_practices = [p["practice"] for p in practices]
    else:
        db.add(metric)
    await db.commit()

    return {
        "score": round(final_score, 1),
        "grade": grade,
        "co2_offset_kg": round(total_offset, 2),
        "total_emissions_kg": round(total_emissions, 2),
        "net_kg": net_kg,
        "verified_practices": [p["practice"] for p in practices],
        "components": {
            "base_score": base_score,
            "practice_bonus": round(practice_bonus, 2),
            "emission_penalty": round(emission_penalty, 2),
        },
        "sequestration_breakdown": seq_components,
        "emission_breakdown": emissions_data["breakdown"],
        "recommendation": recommendation,
    }


# ---------------------------------------------------------------------------
# Carbon markets
# ---------------------------------------------------------------------------
# Catalog of carbon-credit schemes. `regions` is None => nationwide; otherwise a
# list of region/district substrings that must match `location`. (#22)
_CARBON_MARKETS = [
    {"name": "Bangladesh Green Fund", "type": "Government", "benefit": "Cash subsidy per bigha",
     "min_score": 60, "regions": None, "requires_practice": False},
    {"name": "Global Carbon Credit Exchange", "type": "International", "benefit": "Carbon credits in USD",
     "min_score": 80, "regions": None, "requires_practice": True},
    {"name": "Eco-Agro Partnership", "type": "Private", "benefit": "Reduced interest on loans",
     "min_score": 40, "regions": None, "requires_practice": False},
]
# Region/district-specific schemes, appended only when `location` matches.
_REGION_CARBON_MARKETS: List[Dict[str, Any]] = []


def get_carbon_market_opportunities(score: float, location: str) -> List[Dict[str, Any]]:
    """Matches the farmer's score to potential carbon-credit schemes with rationale.

    Eligibility is score-based AND region-aware: a scheme only applies when its
    ``regions`` is None (nationwide) or matches the provided ``location``
    (region/district substring). Region-specific schemes are appended when they
    apply; results are ranked (eligible first, then by lowest qualifying
    threshold). A safe nationwide fallback (the three base schemes) is always
    returned even when ``location`` is empty/unknown. (#22)
    """
    loc = (location or "").lower().strip()

    def _applies(regions: Optional[List[str]]) -> bool:
        if not regions:
            return True
        if not loc:
            return False
        return any(r.lower() in loc or loc in r.lower() for r in regions)

    catalog = list(_CARBON_MARKETS)
    for m in _REGION_CARBON_MARKETS:
        if _applies(m.get("regions")):
            catalog.append(m)

    out = []
    for opt in catalog:
        region_match = _applies(opt.get("regions"))
        eligible = score >= opt["min_score"] and region_match
        rationale = (
            f"Score {score:.0f} meets minimum {opt['min_score']}."
            if eligible else
            f"Score {score:.0f} below minimum {opt['min_score']}."
        )
        out.append({
            "name": opt["name"], "type": opt["type"], "benefit": opt["benefit"],
            "eligible": eligible, "rationale": rationale,
            "region_match": region_match,
        })

    # Rank: eligible schemes first, then by lowest qualifying threshold.
    out.sort(key=lambda o: (not o["eligible"], o["name"]))
    return out


# ---------------------------------------------------------------------------
# OO facade
# ---------------------------------------------------------------------------
# The module-level functions above are the canonical implementation used by the
# Phase 2 FastAPI endpoints (they take an ``AsyncSession`` + ``user_id`` and hit
# the DB). ``SustainabilityService`` is a thin, optional object wrapper that:
#   * exposes the lightweight, entry-list-driven helpers the tests / callers
#     expect (no DB required), and
#   * provides ``*_from_db`` facades that delegate to the real functions when a
#     db session is supplied.
# Adding this class leaves the function-based callers fully intact.
_PRACTICE_ALIASES = {
    "composting": "organic_compost",
    "cover_cropping": "cover-cropping",
    "cover cropping": "cover-cropping",
    # Drip irrigation is a WATER-efficiency practice, NOT reduced nitrogen use.
    "drip_irrigation": "water_efficiency",
    "no_till": "no-till",
    "no-till": "no-till",
    "agroforestry": "agroforestry",
    "reduced_nitrogen": "reduced-nitrogen",
    "reduced nitrogen": "reduced-nitrogen",
}


class SustainabilityService:
    """Object wrapper over the sustainability/carbon functions.

    ``db`` / ``user_id`` are only needed for the ``*_from_db`` helpers; the
    synchronous, list-based helpers (``calculate_carbon_footprint``,
    ``detect_sustainable_practices``, ``generate_scorecard``) work without a DB.
    """

    def __init__(
        self,
        db: Optional[AsyncSession] = None,
        user_id: Optional[str] = None,
    ):
        self.db = db
        self.user_id = user_id

    # --- lightweight, entry-list driven helpers (no DB) -------------------
    def calculate_carbon_footprint(self, entries: List[Any]) -> Dict[str, Any]:
        """Compute emissions from a list of diary entry-like objects.

        Returns a dict containing ``total_emissions_kg_co2`` (and an
        ``emissions`` alias) so callers/tests can read either key.
        """
        events = parse_input_events(entries or [])
        total = 0.0
        breakdown = []
        for ev in events:
            ef_key = ev["emission_factor_key"]
            if not ef_key:
                continue
            factor = EMISSION_FACTORS[ef_key]
            emission = ev["canonical_quantity"] * factor
            total += emission
            breakdown.append({
                "type": ev["type"],
                "quantity": ev["canonical_quantity"],
                "unit": ev["canonical_unit"],
                "factor": factor,
                "emission_kg": round(emission, 2),
                "confidence": ev["confidence"],
            })
        return {
            "total_emissions_kg_co2": round(total, 2),
            "total_emissions_kg": round(total, 2),
            "emissions": round(total, 2),
            "unit": "kg CO2-eq",
            "breakdown": breakdown,
            "unparsed_cost_entries": sum(
                1 for e in events if e["emission_factor_key"] is None
            ),
        }

    def detect_sustainable_practices(self, entries: List[Any]) -> List[Dict[str, Any]]:
        """Detect sustainable practices from a list of diary entries.

        Prefers structured ``category``/``description`` signals (high confidence)
        and falls back to fuzzy keyword matching on notes (capped confidence). (#23)
        """
        found: Dict[str, Any] = {}

        def _record(practice: str, confidence: float, evidence: List[str]) -> None:
            cur = found.get(practice, {"confidence": 0.0, "evidence": []})
            cur["confidence"] = max(cur["confidence"], confidence)
            for ev in evidence:
                if ev not in cur["evidence"]:
                    cur["evidence"].append(ev)
            found[practice] = cur

        for e in (entries or []):
            cat = getattr(e, "category", None)
            if not isinstance(cat, str):
                cat = ""
            cat = cat.lower().strip()
            notes = getattr(e, "notes", None)
            if not isinstance(notes, str):
                notes = getattr(e, "description", None)
            if not isinstance(notes, str):
                notes = ""
            notes = notes.lower()

            structured = CATEGORY_TO_PRACTICE.get(cat)
            if structured:
                _record(structured, 0.9, [f"category:{cat}"])

            for practice, keywords in PRACTICE_KEYWORDS.items():
                hits = [kw for kw in keywords if kw in notes]
                if hits:
                    conf = min(0.8, 0.5 + 0.25 * len(hits))
                    _record(practice, conf, hits)

        detected = [
            {"practice": p, "confidence": round(v["confidence"], 2), "evidence": v["evidence"]}
            for p, v in found.items()
        ]
        return detected

    def generate_scorecard(
        self,
        emissions: Optional[Dict[str, Any]] = None,
        practices: Optional[List[Any]] = None,
        offsets: float = 0.0,
    ) -> Dict[str, Any]:
        """Build an explainable scorecard from precomputed inputs (no DB)."""
        emissions = emissions or {}
        practices = practices or []
        total_emissions = float(
            emissions.get("total_emissions_kg_co2")
            or emissions.get("total_emissions_kg")
            or 0.0
        )

        canonical: List[str] = []
        for p in practices:
            if isinstance(p, dict):
                name = p.get("practice") or p.get("name") or ""
            else:
                name = str(p)
            key = _PRACTICE_ALIASES.get(name) or (
                name if name in SEQUESTRATION_FACTORS else None
            )
            if key:
                canonical.append(key)

        practice_bonus = 0.0
        for key in canonical:
            spec = SEQUESTRATION_FACTORS.get(key)
            if spec:
                practice_bonus += spec["value"] * 0.05
        practice_bonus = min(40.0, practice_bonus)

        emission_penalty = min(30.0, total_emissions / REFERENCE_EMISSIONS * 30.0)
        # Calibration: anchored at 0 (see get_sustainability_scorecard) so a
        # no-data farmer scores ~0, not a misleading 50/"C".
        base_score = 0.0
        final_score = max(
            0.0, min(100.0, base_score + practice_bonus - emission_penalty)
        )
        net = round(float(offsets) - total_emissions, 2)
        grade = "A" if final_score > 80 else "B" if final_score > 60 else "C"

        return {
            "score": round(final_score, 1),
            "grade": grade,
            "co2_offset_kg": round(float(offsets), 2),
            "total_emissions_kg": round(total_emissions, 2),
            "net_kg": net,
            "verified_practices": canonical,
        }

    # --- DB-backed facades over the module-level functions -----------------
    def parse(self, entries: List[Any]) -> List[Dict[str, Any]]:
        return parse_input_events(entries)

    def market_opportunities(self, score: float, location: str = "") -> List[Dict[str, Any]]:
        return get_carbon_market_opportunities(score, location)

    async def footprint_from_db(self) -> Dict[str, Any]:
        if self.db is None or self.user_id is None:
            raise RuntimeError(
                "SustainabilityService needs db + user_id for DB-backed calls"
            )
        return await calculate_carbon_footprint(self.db, self.user_id)

    async def verify_from_db(self) -> List[Dict[str, Any]]:
        if self.db is None or self.user_id is None:
            raise RuntimeError(
                "SustainabilityService needs db + user_id for DB-backed calls"
            )
        return await verify_sustainable_practices(self.db, self.user_id)

    async def scorecard_from_db(self) -> Dict[str, Any]:
        if self.db is None or self.user_id is None:
            raise RuntimeError(
                "SustainabilityService needs db + user_id for DB-backed calls"
            )
        return await get_sustainability_scorecard(self.db, self.user_id)
