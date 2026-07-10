"""Shared, structured output contracts for the intelligence layer.

Every prediction/advisory produced by the intelligence layer carries the same
shape so the frontend can render it consistently and honestly (source,
confidence, simulated flag, provenance).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class Source:
    """A retrieved knowledge document cited in an answer."""

    id: str
    title: str
    snippet: str
    url: Optional[str] = None
    score: float = 0.0


@dataclass
class ToolTrace:
    """Audit record of a tool (domain service) call made while answering."""

    tool: str
    called: bool
    query: Optional[str] = None
    result_summary: Optional[str] = None
    provenance: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class PredictionProvenance:
    """Where a number came from, so we never silently fake data."""

    source: str  # e.g. "nasa_power", "historical_dam", "simulated"
    confidence: float
    simulated: bool = False
    notes: Optional[str] = None


@dataclass
class IntelligenceResult:
    """The full, structured outcome of an intelligence query."""

    answer: str
    sources: List[Source] = field(default_factory=list)
    tool_traces: List[ToolTrace] = field(default_factory=list)
    context_used: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    simulated_data_used: bool = False
    language: str = "en"
    error: Optional[str] = None

    def to_payload(self) -> Dict[str, Any]:
        """Serialize for the API. None fields are dropped for clean JSON."""
        return asdict(self)


@dataclass
class FarmerContext:
    """Assembled, structured view of the farmer passed to every agent."""

    district: Optional[str] = None
    upazila: Optional[str] = None
    crops: List[str] = field(default_factory=list)
    land_area_bigha: Optional[float] = None
    experience_years: Optional[int] = None
    phone: Optional[str] = None
    gps: Optional[Dict[str, float]] = None
    season: Optional[str] = None
    recent_diary: List[Dict[str, Any]] = field(default_factory=list)
    memory_facts: List[Dict[str, Any]] = field(default_factory=list)
    formatted: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
