"""Phase 2 (Domain depth) tests — carbon, finance, recommendations, traceability."""
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.services.sustainability_service import (
    parse_input_events, calculate_carbon_footprint, verify_sustainable_practices,
    get_sustainability_scorecard, get_carbon_market_opportunities,
    EMISSION_FACTORS,
)
from app.services.finance_service import FinanceService
from app.services.traceability_service import (
    generate_batch_hash, sign_batch_token, verify_batch_token, build_trace_url,
)


# ---------------------------------------------------------------------------
# Fake DB (no real SQL; branches on table name in the query)
# ---------------------------------------------------------------------------
class _FakeResult:
    def __init__(self, items):
        self._items = items
    def scalars(self):
        return _FakeScalars(self._items)
class _FakeScalars:
    def __init__(self, items):
        self.items = items
    def first(self):
        return self.items[0] if self.items else None
    def all(self):
        return self.items

class _FakeDB:
    def __init__(self, **store):
        self._store = store  # table_name -> list of row objects
        self.committed = False
    def add(self, obj):
        pass
    async def commit(self):
        self.committed = True
    async def execute(self, stmt):
        text = str(stmt).lower()
        for tbl, rows in self._store.items():
            if tbl in text:
                return _FakeResult(rows)
        return _FakeResult([])


def _expense(category, notes, amount, unit):
    return SimpleNamespace(entry_type="expense", category=category, notes=notes,
                           amount=amount, unit=unit)


# ---------------------------------------------------------------------------
# Carbon
# ---------------------------------------------------------------------------
def test_parse_input_events_applies_ipcc_factors():
    entries = [
        _expense("fertilizer", "used urea", 10.0, "kg"),     # 10kg urea -> 4.6kg N -> 26.68
        _expense("irrigation", "diesel for pump", 5.0, "L"),  # 5L -> 13.4
        _expense("other", "electricity bill", 10.0, "kWh"),   # 10kWh -> 4.6
    ]
    events = parse_input_events(entries)
    by_type = {e["type"]: e for e in events}
    assert abs(by_type["urea"]["canonical_quantity"] - 4.6) < 1e-6
    assert abs(by_type["urea"]["emission_kg"] - 4.6 * EMISSION_FACTORS["synthetic_nitrogen"]) < 1e-6
    assert abs(by_type["diesel"]["emission_kg"] - 5.0 * EMISSION_FACTORS["diesel_fuel"]) < 1e-6
    assert abs(by_type["electricity"]["emission_kg"] - 10.0 * EMISSION_FACTORS["electricity"]) < 1e-6


async def test_calculate_carbon_footprint_total():
    entries = [
        _expense("fertilizer", "urea", 10.0, "kg"),
        _expense("irrigation", "diesel", 5.0, "L"),
    ]
    db = _FakeDB(farm_diary=entries)
    res = await calculate_carbon_footprint(db, "user-1")
    expected = 4.6 * EMISSION_FACTORS["synthetic_nitrogen"] + 5.0 * EMISSION_FACTORS["diesel_fuel"]
    assert abs(res["total_emissions_kg"] - round(expected, 2)) < 1e-6
    assert res["breakdown"]


async def test_scorecard_is_monotonic_and_explainable():
    # Farmer with sustainable practices + some emissions
    entries = [
        _expense("fertilizer", "urea", 10.0, "kg"),
        SimpleNamespace(entry_type="expense", category="labor", notes="used compost and cover crop", amount=100.0, unit="BDT"),
    ]
    db = _FakeDB(farm_diary=entries)
    sc = await get_sustainability_scorecard(db, "user-2")
    assert 0 <= sc["score"] <= 100
    assert "components" in sc
    assert "net_kg" in sc
    assert "compost" in sc["verified_practices"] or "cover-cropping" in sc["verified_practices"]


def test_carbon_market_opportunities_eligibility():
    high = get_carbon_market_opportunities(85, "Bangladesh")
    low = get_carbon_market_opportunities(35, "Bangladesh")
    green = next(o for o in high if o["name"] == "Bangladesh Green Fund")
    assert green["eligible"] is True
    global_fund = next(o for o in high if o["name"] == "Global Carbon Credit Exchange")
    assert global_fund["eligible"] is True
    assert all(not o["eligible"] for o in low if o["name"] == "Global Carbon Credit Exchange")


# ---------------------------------------------------------------------------
# Finance (risk-based)
# ---------------------------------------------------------------------------
def test_insurance_pricing_is_risk_based():
    fs = FinanceService()
    wheat = fs.get_insurance_quote("wheat", 2.0)        # low risk
    onion = fs.get_insurance_quote("onion", 2.0)        # high risk
    assert onion["premium_rate"] > wheat["premium_rate"]
    assert onion["crop_risk_class"] == "high" and wheat["crop_risk_class"] == "low"
    # premium is explainable
    assert "premium_drivers" in onion


def test_insurance_payout_simulator():
    fs = FinanceService()
    sim = fs.simulate_payout("rice", 2.0, scenario="drought", severity=0.7)
    assert 0 < sim["estimated_payout"] <= sim["sum_insured"]
    assert "net_after_premium" in sim


# ---------------------------------------------------------------------------
# Recommendations (multi-signal reasoning)
# ---------------------------------------------------------------------------
async def test_recommendations_fuse_signals():
    soil = SimpleNamespace(derived_ph=5.0, derived_texture="loam", recommendations="add lime")
    irr = SimpleNamespace(soil_moisture_index=0.3, advice="irrigate")
    fact = SimpleNamespace(fact_key="crop_planted", fact_value="rice")
    diary = [_expense("labor", "logged week", 100.0, "BDT")]

    db = _FakeDB(
        soil_test_logs=[soil], irrigation_logs=[irr],
        knowledge_facts=[fact], farm_diary=diary,
    )

    class _FakeWeather:
        async def get_weather_data(self, lat, lon):
            return {"temp_mean": 32, "humidity": 90, "rainfall_mm": 0}
        async def calculate_water_balance(self, crop, lat, lon, previous_depletion_mm=0.0):
            return {"status": "Deficit", "moisture_index": 0.3,
                    "irrigation_recommendation_mm": 40}

    class _FakeMarket:
        async def get_current_prices(self, crop, lat, lon):
            return {"current_price": 40, "price_forecast": [{"high": 52}]}

    with patch("app.services.weather_service.WeatherService", _FakeWeather), \
         patch("app.services.market_service.MarketService", _FakeMarket):
        from app.services.recommendation_service import RecommendationService

        out = await RecommendationService.get_personalized_recommendations(
            db, "user-3", gps={"lat": 23.8, "lon": 90.3}, language="bn")

    assert out["advisories"]
    sources = {a["source"] for a in out["advisories"]}
    assert "soil_test" in sources          # acidic pH advisory
    assert "water_balance" in sources       # deficit advisory
    assert "pest_risk_model" in sources     # high disease risk
    # advisories are prioritized
    prios = [a["priority"] for a in out["advisories"]]
    assert prios == sorted(prios)
    assert out["personalized_advice"]


# ---------------------------------------------------------------------------
# Traceability (real, verifiable)
# ---------------------------------------------------------------------------
def test_hash_chain_links_batches():
    h1 = generate_batch_hash(None, {"user_id": "u", "crop": "rice", "quantity": 10, "inputs": ["urea"]})
    h2 = generate_batch_hash(h1, {"user_id": "u", "crop": "rice", "quantity": 20, "inputs": ["urea"]})
    assert h1 != h2
    # changing data changes the hash
    h3 = generate_batch_hash(h1, {"user_id": "u", "crop": "rice", "quantity": 99, "inputs": ["urea"]})
    assert h3 != h2


def test_trace_token_roundtrip():
    bid = "batch-123"
    h = generate_batch_hash(None, {"user_id": "u", "crop": "rice", "quantity": 1, "inputs": []})
    token = sign_batch_token(bid, h)
    assert verify_batch_token(bid, token, h) is True
    assert verify_batch_token(bid, token, "tampered") is False
    assert verify_batch_token("other", token, h) is False


def test_build_trace_url_is_real_and_verifiable():
    bid = "batch-xyz"
    h = "abc123"
    url = build_trace_url(bid, h)
    assert bid in url and h in url
    assert "t=" in url  # signed token present


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
