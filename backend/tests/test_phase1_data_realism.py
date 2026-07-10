"""Phase 1 (Data realism) tests — no random mocks, real distances, GDD, honesty."""
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.services import market_provider as mp
from app.services.market_provider import SimulatedProvider, get_provider, haversine
from app.services.agronomy_service import AgronomyService
from app.intelligence.tools import detect_crop


# ---------------------------------------------------------------------------
# Market: no random mock prices, real distances, provenance
# ---------------------------------------------------------------------------
def test_provider_prices_are_deterministic_and_seasonal():
    p = SimulatedProvider()
    d1 = __import__("datetime").date(2026, 7, 8)
    d2 = __import__("datetime").date(2026, 7, 8)
    assert p.current_price("rice", d1) == p.current_price("rice", d2)
    # different months differ via seasonal curve
    jan = p.current_price("rice", __import__("datetime").date(2026, 1, 15))
    jul = p.current_price("rice", __import__("datetime").date(2026, 7, 15))
    assert jan != jul


def test_get_provider_defaults_to_simulated():
    prov = get_provider()
    assert prov.source == "simulated"
    assert prov.simulated is True


def test_nearby_mandis_use_real_haversine_distances():
    p = SimulatedProvider()
    rows = p.nearby_mandis("rice", 23.756, 90.395)  # near Karwan Bazar
    assert rows
    # distances are real floats, not random ints
    assert all(isinstance(r["distance_km"], float) for r in rows)
    # nearest market should be the one at the same coords (distance ~0)
    assert rows[0]["distance_km"] < 5.0
    # sorted ascending by distance
    dists = [r["distance_km"] for r in rows]
    assert dists == sorted(dists)


def test_haversine_sanity():
    # Dhaka -> roughly Chittagong ~250 km
    d = haversine(23.756, 90.395, 22.317, 91.831)
    assert 200 < d < 320


async def test_market_service_no_random_prices():
    # Prevent any real redis connection attempt during the test.
    class _DeadRedis:
        @staticmethod
        def from_url(*a, **k):
            raise RuntimeError("no redis in tests")

    with patch("app.services.market_service.Redis", _DeadRedis):
        from app.services.market_service import MarketService

        svc = MarketService()
        data = await svc.get_current_prices("rice", 23.756, 90.395)
        assert data["source"] == "simulated"
        assert data["simulated"] is True
        assert "current_price" in data and data["current_price"] > 0
        # mandis carry real distances
        for m in data["current_prices"]:
            assert isinstance(m["distance_km"], float)
        # forecast carries uncertainty bands
        assert data["price_forecast"]
        assert "low" in data["price_forecast"][0] and "high" in data["price_forecast"][0]


async def test_market_trend_forecast_has_bands():
    class _DeadRedis:
        @staticmethod
        def from_url(*a, **k):
            raise RuntimeError("no redis")

    with patch("app.services.market_service.Redis", _DeadRedis):
        from app.services.market_service import MarketService

        svc = MarketService()
        res = await svc.predict_price_trend("potato", session=None)
        assert res["simulated"] is True
        assert res["price_forecast"]
        assert "low" in res["price_forecast"][0]
        assert res["trend_direction"] in ("up", "down", "flat")


# ---------------------------------------------------------------------------
# Agronomy: GDD phenology + probability risk scorer
# ---------------------------------------------------------------------------
def test_gdd_accumulation():
    temps = [{"min": 20, "max": 30}] * 10  # 15 GDD/day
    assert AgronomyService.accumulate_gdd(temps) == 150.0


def test_predict_growth_stage_from_gdd():
    temps = [{"min": 20, "max": 30}] * 10  # 150 GDD
    out = AgronomyService.predict_growth_stage("rice", None, temps)
    assert out["cumulative_gdd"] == 150.0
    assert out["stage"] == "Germination"
    assert out["next_stage"] == "Seedling/Tillering"
    assert 0 < out["progress_to_next"] < 1


def test_evaluate_risk_probabilities_and_no_hardcoded_district():
    risks = AgronomyService.evaluate_risk(
        {"temp": 30, "humidity": 92, "moisture": 8, "leaf_wetness_hours": 9, "rainfall_mm": 0}
    )
    assert risks
    for r in risks:
        assert 0.0 <= r["probability"] <= 1.0
        assert r["level"] in ("Low", "Moderate", "High")
        assert "Pabna" not in str(r["factor"])
    disease = next(r for r in risks if r["type"] == "Disease")
    assert disease["probability"] >= 0.6  # very favorable -> High
    drought = next(r for r in risks if r["type"] == "Environmental")
    assert drought["probability"] >= 0.6


def test_evaluate_risk_low_conditions():
    risks = AgronomyService.evaluate_risk(
        {"temp": 26, "humidity": 70, "moisture": 40, "leaf_wetness_hours": 0, "rainfall_mm": 10}
    )
    for r in risks:
        assert r["probability"] < 0.6


# ---------------------------------------------------------------------------
# Yield: honest estimated NDVI
# ---------------------------------------------------------------------------
async def test_ndvi_estimated_and_weather_dependent():
    class _FakeWeatherCls:
        _rain = 50.0
        _temp = 28.0

        def __init__(self, *a, **k):
            pass

        async def get_weather_data(self, lat, lon):
            return {"rainfall_mm": _FakeWeatherCls._rain, "temp_mean": _FakeWeatherCls._temp}

    with patch("app.services.weather_service.WeatherService", _FakeWeatherCls):
        from app.services.yield_service import get_satellite_ndvi, NDVI_ESTIMATED

        assert NDVI_ESTIMATED is True
        _FakeWeatherCls._rain, _FakeWeatherCls._temp = 250.0, 27.0
        wet = await get_satellite_ndvi(23.8, 90.3)
        _FakeWeatherCls._rain, _FakeWeatherCls._temp = 5.0, 35.0
        dry = await get_satellite_ndvi(23.8, 90.3)
        assert 0.2 <= wet <= 0.9 and 0.2 <= dry <= 0.9
        assert wet > dry  # more rain -> greener estimate


# ---------------------------------------------------------------------------
# Training scripts produce valid, agronomy-grounded data
# ---------------------------------------------------------------------------
def test_yield_training_data_is_agronomy_grounded():
    from scripts.train_yield_model import generate_agronomy_data

    df = generate_agronomy_data(n_samples=200, seed=1)
    assert len(df) == 200
    assert {"ndvi", "rainfall_mm", "temp_mean", "historical_avg_yield",
            "input_cost_normalized", "yield_tons_per_bigha"} <= set(df.columns)
    # NDVI and yield should be positively correlated (model learns real signal)
    corr = df["ndvi"].corr(df["yield_tons_per_bigha"])
    assert corr > 0.3


def test_market_training_history_is_seasonal():
    from scripts.train_market_model import generate_synthetic_history

    df = generate_synthetic_history("rice", days=120)
    assert len(df) == 120
    assert df["y"].min() > 0
    # bounded, not an unbounded random walk
    assert df["y"].max() < df["y"].mean() * 3


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
