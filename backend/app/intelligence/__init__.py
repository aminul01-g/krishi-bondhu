"""Intelligence layer for KrishiBondhu (Phase 0).

Exposes the orchestrator that assembles farmer context, retrieves knowledge
(RAG), calls domain-service tools for live evidence, and synthesizes a grounded,
cited answer.
"""
from app.intelligence.orchestrator import IntelligenceOrchestrator
from app.intelligence.schemas import (
    FarmerContext, IntelligenceResult, Source, ToolTrace, PredictionProvenance,
)

__all__ = [
    "IntelligenceOrchestrator",
    "FarmerContext", "IntelligenceResult", "Source", "ToolTrace", "PredictionProvenance",
]
