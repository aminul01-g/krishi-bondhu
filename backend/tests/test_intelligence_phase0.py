"""Phase 0 intelligence-layer tests (no LLM / network required).

Covers: crop detection, intent routing, ET0 radiation correction, RAG keyword
fallback, prompt construction, confidence, and a full orchestration flow with
the DB + tools mocked.
"""
import asyncio
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.intelligence.tools import detect_crop, run_tool, TOOL_REGISTRY
from app.intelligence.intent import classify_intent
from app.intelligence.farmer_context import FarmerContextAssembler, FarmerContext
from app.intelligence.retrieval import RetrievalLayer
from app.intelligence.orchestrator import IntelligenceOrchestrator
from app.intelligence.schemas import Source, ToolTrace


# ---------------------------------------------------------------------------
# Pure units
# ---------------------------------------------------------------------------
def test_detect_crop_bengali_and_english():
    assert detect_crop("আমার ধান এর দাম কত?") == "rice"
    assert detect_crop("How much potato can I yield?") == "potato"
    assert detect_crop("আলু চাষ") == "potato"
    assert detect_crop("tell me about the weather") is None


def test_classify_intent_routes_tools():
    water = classify_intent("আমার ধানে সেচ দিতে হবে কি?")
    assert "water_balance" in water["tools"]
    assert "retrieval" in water["tools"]
    assert "memory" in water["tools"]

    market = classify_intent("What is the price of rice today?")
    assert "market" in market["tools"]

    general = classify_intent("hello there")
    # default tools for a non-specific query
    assert set(general["tools"]) >= {"weather", "retrieval", "memory"}


def test_extraterrestrial_radiation_is_physical():
    from app.services.weather_service import WeatherService

    # Dhaka ~23.8 N, mid-July (day ~195). Tropical Ra should be positive and
    # in a plausible band (roughly 11-17 mm/day), NOT surface insolation.
    ra = WeatherService.calculate_extraterrestrial_radiation(23.8, 195)
    assert ra > 0
    assert 8.0 <= ra <= 20.0

    # Southern hemisphere / different day should differ
    ra2 = WeatherService.calculate_extraterrestrial_radiation(-23.8, 15)
    assert isinstance(ra2, float)
    assert ra2 >= 0


def test_calculate_et0_uses_provided_ra():
    from app.services.weather_service import WeatherService

    # ET0 must respond to Ra, i.e. feeding real extraterrestrial radiation
    # (not surface solar) changes the result.
    et0_surface_like = WeatherService().calculate_et0(32.0, 24.0, ra=13.5)
    et0_real_ra = WeatherService().calculate_et0(32.0, 24.0, ra=15.8)
    assert et0_real_ra != et0_surface_like
    assert et0_real_ra > 0


# ---------------------------------------------------------------------------
# RAG keyword fallback (force embeddings off)
# ---------------------------------------------------------------------------
def test_retrieval_keyword_fallback_when_model_unavailable():
    layer = RetrievalLayer()
    layer._emb = None
    layer._model_available = False
    with patch(
        "app.services.embedding_service.encode_texts", side_effect=RuntimeError("no model")
    ):
        sources = layer.retrieve("ধান এর রোগ পোকা ব্যবস্থাপনা", k=3)
    assert sources, "keyword fallback should still return results"
    assert all(isinstance(s, Source) for s in sources)
    assert sources[0].score > 0


def test_retrieval_semantic_returns_ranked_sources():
    layer = RetrievalLayer()
    sources = layer.retrieve("rice stem borer management", k=3)
    assert sources
    # top result should be the stem-borer doc
    assert sources[0].id == "stem-borer"


# ---------------------------------------------------------------------------
# Orchestrator prompt + confidence (no LLM)
# ---------------------------------------------------------------------------
def test_build_prompt_includes_context_and_citations():
    ctx = FarmerContext(
        district="Tangail", crops=["rice"], season="Kharif-II (Monsoon)",
        formatted="Farmer context: District=Tangail, Crops=[rice], Season=Kharif-II (Monsoon)",
    )
    sources = [Source(id="stem-borer", title="Rice stem borer", snippet="xyz", score=0.9)]
    prompt = IntelligenceOrchestrator._build_prompt(
        "how to control stem borer", ctx, sources, ["- weather: ok"], None, "bn"
    )
    assert "Farmer context:" in prompt
    assert "[1]" in prompt
    assert "stem borer" in prompt
    assert "Bengali" in prompt


def test_confidence_caps_when_simulated():
    ctx = FarmerContext(formatted="x")
    traces = [ToolTrace(tool="market", called=True, provenance={"simulated": True})]
    c = IntelligenceOrchestrator._confidence(ctx, traces, simulated=True)
    assert c <= 0.7
    c2 = IntelligenceOrchestrator._confidence(ctx, [ToolTrace(tool="m", called=True)], simulated=False)
    assert c2 > c


# ---------------------------------------------------------------------------
# Full orchestration with mocked DB + tools (no network, no LLM)
# ---------------------------------------------------------------------------
class _FakeScalars:
    def __init__(self, items): self.items = items
    def first(self): return self.items[0] if self.items else None
    def all(self): return self.items


class _FakeResult:
    def __init__(self, items): self._s = _FakeScalars(items)
    def scalars(self): return self._s


class _FakeDB:
    def __init__(self, profile=None, diary=None, facts=None):
        self._profile = profile
        self._diary = diary or []
        self._facts = facts or []

    async def execute(self, stmt):
        text = str(stmt)
        if "farmer_profiles" in text:
            return _FakeResult([self._profile] if self._profile else [])
        if "farm_diary" in text:
            return _FakeResult(self._diary)
        if "knowledge_facts" in text:
            return _FakeResult(self._facts)
        return _FakeResult([])


async def _fake_run_tool(name, db, ctx, message, gps, external_id=""):
    if name == "weather":
        return ToolTrace(tool="weather", called=True,
                         result_summary="temp_mean=29.0", provenance={"source": "nasa_power"})
    if name == "market":
        return ToolTrace(tool="market", called=True,
                         result_summary="current_price=42", provenance={"source": "simulated", "simulated": True})
    return ToolTrace(tool=name, called=False, error="n/a")


async def test_orchestrator_respond_full_flow():
    db = _FakeDB(
        profile=SimpleNamespace(
            district="Tangail", upazila="Sakhipur", crops=["rice"],
            land_area_bigha=3.0, farming_experience_years=10, phone_number="01xxx",
        ),
        diary=[SimpleNamespace(date=None, entry_type="expense", category="fertilizer",
                               crop="rice", amount=500.0, unit="BDT", notes="urea")],
        facts=[SimpleNamespace(fact_key="soil_status", fact_value="loam", confidence=1.0)],
    )
    orch = IntelligenceOrchestrator()
    with patch("app.intelligence.orchestrator.run_tool", _fake_run_tool), \
         patch.object(IntelligenceOrchestrator, "_synthesize",
                      return_value="Use balanced fertilizer and monitor for stem borer."):
        result = await orch.respond(
            db, message="ধান এর ফলন ও দাম কেমন হবে? সেচ দিতে হবে?",
            user_id_int=1, external_id="ext-1",
            gps={"lat": 23.8, "lon": 90.3}, history=None, language="bn",
        )

    assert isinstance(result.answer, str) and result.answer
    assert result.context_used["district"] == "Tangail"
    assert result.context_used["crops"] == ["rice"]
    called_tools = {t.tool for t in result.tool_traces if t.called}
    # intent selected yield + market + water_balance; market was faked as called
    assert "market" in called_tools
    assert any(t.tool == "water_balance" for t in result.tool_traces)
    assert any(t.tool == "yield" for t in result.tool_traces)
    # market tool reported simulated -> flag should be set
    assert result.simulated_data_used is True
    assert 0 < result.confidence <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
