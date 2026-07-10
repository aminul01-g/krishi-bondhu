"""DAM adapter + robust Prophet wiring tests (offline, fully mocked).

These prove the live-feed integration path WITHOUT requiring network access
or an installed `prophet` package:

  * Live DAM path returns ``provenance == 'live_dam'`` and the normalized schema.
  * Network / shape failures fall back to ``None`` / ``'simulated'`` WITHOUT raising.
  * Prophet-absent path (import error / fit error) uses the seasonal fallback.
  * Prophet-present path (mocked) is actually exercised on live DAM history.
"""
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pytest


# ---------------------------------------------------------------------------
# DAM adapter (market_provider.fetch_dam_prices)
# ---------------------------------------------------------------------------
def _fake_httpx_client(json_payload):
    """Build a MagicMock standing in for an `httpx.Client` context manager."""
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = json_payload

    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    client.get.return_value = resp
    return client


def test_fetch_dam_prices_live_returns_normalized_schema():
    from app.services.market_provider import fetch_dam_prices

    payload = {
        "records": [
            {"commodity": "rice", "market": "Karwan Bazar", "modal_price": 65,
             "min_price": 60, "max_price": 70, "date": "2026-07-09"},
            {"commodity": "rice", "market": "Karwan Bazar", "modal_price": 66,
             "min_price": 61, "max_price": 71, "date": "2026-07-10"},
        ]
    }
    with patch("httpx.Client", return_value=_fake_httpx_client(payload)):
        data = fetch_dam_prices("rice", api_url="https://dam.test/api")

    assert data is not None
    assert data["source"] == "live_dam"
    assert data["simulated"] is False
    assert data["current_price"] == 66
    assert len(data["price_history"]) == 2
    assert data["price_history"][0]["date"] == "2026-07-09"
    assert data["current_prices"][0]["mandi"] == "Karwan Bazar"
    assert data["current_prices"][0]["price_bdt_per_kg"] == 66


def test_fetch_dam_prices_handles_min_max_fallback():
    from app.services.market_provider import fetch_dam_prices

    # No modal_price -> derive from min/max average.
    payload = {"prices": [
        {"date": "2026-07-08", "price": 50, "mandi": "Rajshahi"},
        {"date": "2026-07-09", "min_price": 40, "max_price": 60, "market": "Rajshahi"},
    ]}
    with patch("httpx.Client", return_value=_fake_httpx_client(payload)):
        data = fetch_dam_prices("potato", api_url="https://dam.test/api")

    assert data is not None
    # second record: (40+60)/2 = 50; latest dated wins -> 50
    assert data["current_price"] == 50


def test_fetch_dam_prices_network_failure_returns_none_without_raising():
    import httpx
    from app.services.market_provider import fetch_dam_prices

    with patch("httpx.Client", side_effect=httpx.ConnectError("network blocked")):
        data = fetch_dam_prices("rice", api_url="https://dam.test/api")

    assert data is None  # caller falls back to simulation, no exception raised


def test_fetch_dam_prices_bad_shape_returns_none():
    from app.services.market_provider import fetch_dam_prices

    with patch("httpx.Client", return_value=_fake_httpx_client({"unexpected": "blob"})):
        data = fetch_dam_prices("rice", api_url="https://dam.test/api")

    assert data is None


def test_fetch_dam_prices_no_api_base_returns_none():
    from app.services.market_provider import fetch_dam_prices

    # Explicitly empty base + no env -> nothing to call.
    data = fetch_dam_prices("rice", api_url="")
    assert data is None


# ---------------------------------------------------------------------------
# Service wiring with live DAM (provenance + no-raise fallback)
# ---------------------------------------------------------------------------
class _DeadRedis:
    @staticmethod
    def from_url(*a, **k):
        raise RuntimeError("no redis in tests")


def _make_service():
    with patch("app.services.market_service.Redis", _DeadRedis):
        from app.services.market_service import MarketService
        return MarketService()


_LIVE_PAYLOAD = {
    "source": "live_dam",
    "simulated": False,
    "current_price": 66.0,
    "price_history": [
        {"date": "2026-07-08", "price": 64.0},
        {"date": "2026-07-09", "price": 65.0},
        {"date": "2026-07-10", "price": 66.0},
    ],
    "current_prices": [{"mandi": "Karwan Bazar", "price_bdt_per_kg": 66.0, "distance_km": None}],
    "confidence": "Live DAM wholesale feed (real observed prices)",
}


async def test_service_get_current_prices_live_dam_provenance():
    svc = _make_service()
    with patch("app.services.market_service.fetch_dam_prices", return_value=_LIVE_PAYLOAD):
        data = await svc.get_current_prices("rice", 23.756, 90.395)

    assert data["provenance"] == "live_dam"
    assert data["source"] == "live_dam"
    assert data["simulated"] is False
    assert data["current_price"] == 66.0
    assert data["price_forecast"]  # bands always present
    assert "low" in data["price_forecast"][0] and "high" in data["price_forecast"][0]


async def test_service_get_current_prices_fallback_to_simulated():
    svc = _make_service()
    with patch("app.services.market_service.fetch_dam_prices", return_value=None):
        data = await svc.get_current_prices("rice", 23.756, 90.395)

    assert data["provenance"] == "simulated"
    assert data["simulated"] is True
    assert data["current_price"] > 0
    assert data["price_forecast"]


async def test_service_predict_trend_live_dam_provenance():
    svc = _make_service()
    with patch("app.services.market_service.fetch_dam_prices", return_value=_LIVE_PAYLOAD):
        res = await svc.predict_price_trend("rice", session=None)

    assert res["provenance"] == "live_dam"
    assert res["source"] == "live_dam"
    assert res["simulated"] is False
    assert res["price_forecast"]
    assert "low" in res["price_forecast"][0]


async def test_service_predict_trend_fallback_to_simulated():
    svc = _make_service()
    with patch("app.services.market_service.fetch_dam_prices", return_value=None):
        res = await svc.predict_price_trend("rice", session=None)

    assert res["provenance"] == "simulated"
    assert res["price_forecast"]
    assert "low" in res["price_forecast"][0]
    assert res["trend_direction"] in ("up", "down", "flat")


async def test_service_predict_trend_prophet_absent_uses_seasonal_fallback():
    """Live DAM history present, but Prophet cannot be imported -> seasonal fallback.

    Verifies the robust wiring: real price data is still surfaced (provenance
    live_dam) while the forecast band comes from the calibrated seasonal model
    instead of crashing.
    """
    svc = _make_service()
    with patch("app.services.market_service.fetch_dam_prices", return_value=_LIVE_PAYLOAD):
        # Force the lazy Prophet import to fail, as it does in this offline env.
        with patch("app.services.market_service.MarketService._prophet_forecast",
                   return_value=None):
            res = await svc.predict_price_trend("rice", session=None)

    assert res["provenance"] == "live_dam"
    assert res["price_forecast"]  # still produced via seasonal fallback
    assert "low" in res["price_forecast"][0]


async def test_service_predict_trend_prophet_present_on_live_history():
    """Mock Prophet to prove the on-the-fly live-DAM forecast path is wired."""
    svc = _make_service()

    class FakeProphet:
        def __init__(self, **kw):
            self.kw = kw

        def fit(self, df):
            self._n = len(df)
            return self

        def make_future_dataframe(self, periods):
            import pandas as pd
            return pd.DataFrame(
                {"ds": pd.date_range("2026-07-01", periods=self._n + periods, freq="D")}
            )

        def predict(self, future):
            future = future.copy()
            future["yhat"] = 72.0
            future["yhat_lower"] = 69.0
            future["yhat_upper"] = 75.0
            return future

    with patch("app.services.market_service.fetch_dam_prices", return_value=_LIVE_PAYLOAD):
        with patch.dict("sys.modules", {"prophet": SimpleNamespace(Prophet=FakeProphet)}):
            res = await svc.predict_price_trend("rice", session=None)

    assert res["provenance"] == "live_dam"
    assert res["predicted_7day"] == 72.0
    assert res["price_forecast"][-1]["price"] == 72.0
    assert res["confidence"].startswith("Live DAM wholesale feed (Prophet")


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
