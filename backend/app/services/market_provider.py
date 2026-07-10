"""Market data providers (Phase 1 — Data realism).

Replaces the old `price = base * random.uniform(0.9, 1.1)` mock with a
*calibrated, reproducible* price model that is honestly flagged as simulated
until a real feed (e.g. DAM / govt Agricultural Marketing Dept) is wired.

Design:
  * `PriceProvider` protocol: `current_price`, `nearby_mandis`, `forecast`.
  * `SimulatedProvider`: seasonal model + stable per-day jitter + real
    haversine distances to known wholesale mandis.
  * `DamProvider`: wraps `fetch_dam_prices` (real DAM/AgMarkNet feed) and returns
    None on any failure so callers transparently fall back to simulation.
  * `fetch_dam_prices(crop, market=None)`: the live adapter — lazy httpx/requests,
    tolerant DAM/AgMarkNet payload mapping, returns None on any failure.
  * `get_provider()` returns the calibrated simulated fallback. The market
    service prefers live DAM on-demand via `fetch_dam_prices`, falling back here.

Every provider exposes `source` and `simulated` so the UI/intelligence layer can
be honest about data provenance.
"""
from __future__ import annotations

import datetime
import hashlib
import logging
import math
import os
from typing import Dict, List, Optional

logger = logging.getLogger("MarketProvider")

# Live Bangladesh DAM (Dept. of Agricultural Marketing) feed configuration.
# Production note: outbound network access is required, and a DAM_API_BASE must
# point at the real DAM/AgMarkNet-style endpoint. Leave unconfigured in dev to
# transparently fall back to the calibrated simulation.
DAM_API_BASE = os.getenv("DAM_API_BASE", "https://dam.gov.bd/api/v1/prices")
DAM_API_KEY = os.getenv("DAM_API_KEY", "")

# Major Bangladesh wholesale markets with approximate coordinates.
MANDI_TABLE = [
    {"name": "Karwan Bazar, Dhaka", "lat": 23.756, "lon": 90.395},
    {"name": "Shyam Bazar, Dhaka", "lat": 23.728, "lon": 90.407},
    {"name": "Rajshahi Sadar Mandi", "lat": 24.374, "lon": 88.601},
    {"name": "Khulna Boro Bazar", "lat": 22.845, "lon": 89.540},
    {"name": "Bogura Mohasthan Hat", "lat": 24.847, "lon": 89.377},
    {"name": "Chittagong Khatunganj", "lat": 22.317, "lon": 91.831},
    {"name": "Sylhet Osmani Market", "lat": 24.899, "lon": 91.871},
    {"name": "Narsingdi Mandi", "lat": 23.933, "lon": 90.718},
]

# Reference wholesale prices (BDT/kg) — approximate Bangladesh 2024/25 normals.
CROP_BASE_PRICES = {
    "rice": 65, "wheat": 45, "potato": 22, "onion": 55, "tomato": 40,
    "brinjal": 35, "chili": 200, "jute": 45, "cabbage": 35, "maize": 30,
    "mango": 80, "garlic": 120,
    "ধান": 28, "গম": 35, "আলু": 22, "পেঁয়াজ": 55, "টমেটো": 40, "বেগুন": 35,
    "মরিচ": 200, "পাট": 45, "ভুট্টা": 30, "আম": 80, "রসুন": 120,
}


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two lat/lon points."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(a)), 1)


def seasonal_multiplier(month: int) -> float:
    """Smooth seasonal price curve: scarcity peaks ~Feb and ~Oct, troughs at harvest."""
    return (
        1.0
        + 0.12 * math.sin(2 * math.pi * (month - 2) / 12)
        + 0.06 * math.sin(2 * math.pi * (month - 10) / 6)
    )


def _stable_jitter(crop: str, day: datetime.date) -> float:
    """Deterministic ±2% variation stable within a calendar day (no flicker)."""
    h = int(hashlib.md5(f"{crop}-{day.isoformat()}".encode()).hexdigest(), 16)
    return 1.0 + ((h % 1000) / 1000.0 - 0.5) * 0.04


class SimulatedProvider:
    source = "simulated"
    simulated = True
    confidence_note = "Calibrated seasonal model (no live DAM feed configured)"

    def current_price(self, crop: str, day: Optional[datetime.date] = None) -> float:
        day = day or datetime.date.today()
        base = CROP_BASE_PRICES.get(crop, 60.0)
        return round(base * seasonal_multiplier(day.month) * _stable_jitter(crop, day), 2)

    def nearby_mandis(
        self, crop: str, lat: Optional[float], lon: Optional[float], top_n: int = 5
    ) -> List[Dict[str, object]]:
        base = CROP_BASE_PRICES.get(crop, 60.0)
        today = datetime.date.today()
        rows = []
        for m in MANDI_TABLE:
            dist = haversine(lat, lon, m["lat"], m["lon"]) if lat is not None and lon is not None else None
            price = base * seasonal_multiplier(today.month) * _stable_jitter(crop, today)
            rows.append(
                {
                    "mandi": m["name"],
                    "price_bdt_per_kg": round(price, 2),
                    "distance_km": dist,
                }
            )
        if lat is not None and lon is not None:
            rows.sort(key=lambda x: (x["distance_km"] is None, x["distance_km"]))
        return rows[:top_n]

    def forecast(self, crop: str, days: int = 7):
        """14-day history (ending today) + `days`-day forecast with uncertainty bands."""
        base = CROP_BASE_PRICES.get(crop, 60.0)
        today = datetime.date.today()
        history, fcast = [], []
        for i in range(13, -1, -1):
            d = today - datetime.timedelta(days=i)
            p = base * seasonal_multiplier(d.month) * _stable_jitter(crop, d)
            history.append({"date": d.isoformat(), "price": round(p, 2)})
        last = history[-1]["price"]
        for i in range(1, days + 1):
            d = today + datetime.timedelta(days=i)
            center = last * (1 + 0.002 * i) * (seasonal_multiplier(d.month) / seasonal_multiplier(today.month))
            spread = 0.03 + 0.01 * i  # widening uncertainty forward in time
            fcast.append(
                {
                    "date": d.isoformat(),
                    "price": round(center, 2),
                    "low": round(center * (1 - spread), 2),
                    "high": round(center * (1 + spread), 2),
                }
            )
        return history, fcast, fcast[-1]["price"]


def _normalize_dam_response(crop: str, raw: object) -> Optional[Dict[str, object]]:
    """Map a DAM/AgMarkNet-style payload into the internal price schema.

    Accepts any of these shapes (the adapter is deliberately tolerant):
      * {"records": [ {commodity, market, modal_price/min_price/max_price, date}, ... ]}
      * {"prices": [ {date, price, mandi?}, ... ]}
      * a bare list of records

    Returns a dict with keys: source, simulated, current_price, price_history
    ([{date, price}]), current_prices ([{mandi, price_bdt_per_kg, distance_km}]),
    confidence. Returns None if the payload cannot be interpreted.
    """
    if not isinstance(raw, (dict, list)):
        return None

    records = None
    if isinstance(raw, dict):
        records = raw.get("records") or raw.get("prices") or raw.get("data")
    if records is None and isinstance(raw, list):
        records = raw
    if not records:
        return None

    points: List[Dict[str, object]] = []
    mandi_rows: Dict[str, float] = {}
    for rec in records:
        if not isinstance(rec, dict):
            continue
        price = rec.get("modal_price", rec.get("price", rec.get("modalPrice")))
        if price is None:
            try:
                price = (float(rec.get("min_price", 0)) + float(rec.get("max_price", 0))) / 2.0
            except (TypeError, ValueError):
                price = None
        if price is None:
            continue
        try:
            price = float(price)
        except (TypeError, ValueError):
            continue
        date = str(rec.get("date", rec.get("ds", "")) or "").strip()
        mandi = rec.get("market", rec.get("mandi", rec.get("commodity", "")))
        points.append({"date": date, "price": price})
        if mandi:
            mandi_rows[mandi] = price  # DAM tends to emit one row per mandi

    if not points:
        return None

    points_sorted = sorted(points, key=lambda p: p["date"] or "0000")
    price_history = [{"date": p["date"], "price": round(p["price"], 2)} for p in points_sorted]
    current_price = price_history[-1]["price"]

    current_prices = [
        {"mandi": m, "price_bdt_per_kg": round(p, 2), "distance_km": None}
        for m, p in mandi_rows.items()
    ]

    return {
        "source": "live_dam",
        "simulated": False,
        "current_price": current_price,
        "price_history": price_history,
        "current_prices": current_prices,
        "confidence": "Live DAM wholesale feed (real observed prices)",
    }


def fetch_dam_prices(
    crop: str,
    market: Optional[str] = None,
    api_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Optional[Dict[str, object]]:
    """Fetch live Bangladesh DAM wholesale prices for a crop.

    Returns the normalized internal price dict (see _normalize_dam_response) or
    None on ANY failure — missing network lib, network error, missing API base,
    bad payload shape — so callers transparently fall back to the simulated
    series. The HTTP client (httpx, falling back to requests) is imported
    LAZILY so this module never hard-requires either dependency.

    Production needs: outbound network access + DAM_API_BASE configured.
    """
    base = api_url or DAM_API_BASE
    key = api_key or DAM_API_KEY
    if not base:
        return None
    try:
        params = {"crop": crop}
        if market:
            params["market"] = market
        headers = {"Accept": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"

        try:
            import httpx

            with httpx.Client(timeout=10.0) as client:
                resp = client.get(base, params=params, headers=headers)
                resp.raise_for_status()
                raw = resp.json()
        except ImportError:
            import requests  # lazy fallback HTTP client

            resp = requests.get(base, params=params, headers=headers, timeout=10.0)
            resp.raise_for_status()
            raw = resp.json()

        return _normalize_dam_response(crop, raw)
    except Exception as e:  # network/timeout/JSON/auth/shape — anything
        logger.warning(f"DAM fetch failed for crop={crop!r}: {e}")
        return None


class DamProvider:
    """Real government/DAM price feed.

    Wraps `fetch_dam_prices`; yields a normalized live payload when the DAM API
    is reachable, else None so callers fall back to the calibrated simulation.
    """

    source = "live_dam"
    simulated = False
    confidence_note = "Live DAM wholesale feed (real observed prices)"

    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None):
        self.api_url = api_url or DAM_API_BASE
        self.api_key = api_key or DAM_API_KEY

    async def fetch(self, crop: str, market: Optional[str] = None):
        return fetch_dam_prices(crop, market=market, api_url=self.api_url, api_key=self.api_key)


_provider: Optional[object] = None


def get_provider():
    """Return the calibrated simulated fallback provider.

    The live DAM feed is fetched on-demand per request via `fetch_dam_prices`
    inside the market service (so it can fail gracefully to simulation when the
    network/API is unavailable), rather than as a persistent provider instance.
    `get_provider()` therefore always returns the simulated fallback, which the
    service uses whenever live DAM data is absent.
    """
    global _provider
    if _provider is None:
        _provider = SimulatedProvider()
    return _provider
