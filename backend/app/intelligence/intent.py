"""Intent routing — decides which tools to call for a query.

Deterministic keyword routing (Bengali + English) keeps it reliable and
testable; an LLM could refine this later without changing the contract.
"""
from __future__ import annotations

from typing import Dict, List

# tool -> trigger substrings (lowercased). Bengali + English + common translit.
INTENT_RULES: List[tuple] = [
    ("water_balance", ["সেচ", "irrigat", "পানি", "water", "et0", "evapotranspir",
                       "খরা", "drought", "soil moisture", "আর্দ্রতা"]),
    ("market", ["দাম", "price", "market", "বাজার", "sell", "ক্রয়", "buy",
                "মূল্য", "cost", "rate", "বিক্রি"]),
    ("yield", ["ফলন", "yield", "production", "ভবিষ্যৎ", "predict", "আশা", "উৎপাদন"]),
    ("weather", ["আবহাওয়া", "weather", "বৃষ্টি", "rain", "তাপমাত্রা",
                 "temperature", "forecast", "ঝড়", "storm"]),
    ("diary", ["খাতা", "diary", "নোট", "note", "লগ", "expense", "আয়", "ব্যয়", "রেকর্ড"]),
]

DEFAULT_TOOLS = ["weather", "retrieval", "memory"]


def classify_intent(message: str) -> Dict[str, List[str]]:
    low = (message or "").lower()
    tools = set()
    for tool, triggers in INTENT_RULES:
        if any(t in low for t in triggers):
            tools.add(tool)
    if not tools:
        tools.update(DEFAULT_TOOLS)
    # retrieval + memory are always useful
    tools.add("retrieval")
    tools.add("memory")
    return {"tools": sorted(tools)}
