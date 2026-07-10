"""Seed knowledge corpus for the RAG retrieval layer.

These documents are the "library" the agent can cite. In production this would
be populated from DAE advisories, scheme booklets, and solved Q&A; here we ship
a curated bilingual starter set so retrieval is meaningful out of the box.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Optional


@dataclass
class KnowledgeDoc:
    id: str
    title: str
    text: str
    category: str  # advisory | scheme | pest | agronomy | market | faq
    tags: List[str] = None
    url: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


CORPUS: List[KnowledgeDoc] = [
    KnowledgeDoc(
        id="rice-aman-calendar",
        title="Aman rice cultivation calendar",
        category="agronomy",
        tags=["rice", "ধান", "aman", "calendar", "planting"],
        text=(
            "Aman rice is transplanted in Bangladesh mainly from mid-June to early August "
            "(Kharif-II). Land should be puddled and leveled. Use 2-3 seedlings per hill at "
            "20x15 cm spacing. Apply urea in 3 splits: 1/3 as basal, 1/3 at tillering, 1/3 at "
            "panicle initiation. Monitor for stem borer and brown planthopper; avoid water stress "
            "during flowering. Harvest when 80-85% grains turn golden."
        ),
    ),
    KnowledgeDoc(
        id="rice-boro-water",
        title="Boro rice water management",
        category="agronomy",
        tags=["rice", "ধান", "boro", "irrigation", "সেচ", "water"],
        text=(
            "Boro rice (Rabi season, planted Nov-Jan) is irrigated. Maintain 5-7 cm standing water "
            "during vegetative stage, allow wetting and drying near maturity to strengthen roots. "
            "Over-irrigation wastes water and increases methane; use alternate wetting and drying "
            "(AWD) to save 15-30% water without yield loss."
        ),
    ),
    KnowledgeDoc(
        id="stem-borer",
        title="Rice stem borer management",
        category="pest",
        tags=["pest", "stem borer", "পোকা", "rice", "ধান"],
        text=(
            "Stem borer causes dead hearts in vegetative stage and white heads at maturity. "
            "Management: use pheromone traps (one per 0.1 ha), conserve egg parasitoids, apply "
            "need-based insecticide only when dead-heart incidence exceeds 5%. Avoid indiscriminate "
            "spraying which kills natural enemies."
        ),
    ),
    KnowledgeDoc(
        id="brown-planthopper",
        title="Brown planthopper (BPH) and hopper burn",
        category="pest",
        tags=["pest", "brown planthopper", "bph", "hopper burn", "ধান", "rice"],
        text=(
            "Brown planthopper sucks phloem and causes 'hopper burn' (patches of drying plants). "
            "Favorable conditions: dense planting, excessive nitrogen, stagnant water. Manage with "
            "resistant varieties, balanced fertilizer, drainage, and only need-based insecticides. "
            "Preserve spiders and beetles that prey on BPH."
        ),
    ),
    KnowledgeDoc(
        id="fertilizer-balance",
        title="Balanced fertilizer recommendation",
        category="agronomy",
        tags=["fertilizer", "সার", "npk", "soil"],
        text=(
            "Base fertilizer on a soil test. General guideline for rice: about 80-100 kg N, 20-25 kg "
            "P2O5, 40-60 kg K2O per hectare, split across the season. Excess nitrogen increases pest "
            "and lodging risk. Use compost and urea deep placement to improve efficiency."
        ),
    ),
    KnowledgeDoc(
        id="market-sell-hold",
        title="When to sell produce",
        category="market",
        tags=["market", "price", "দাম", "sell", "storage"],
        text=(
            "Prices typically rise post-harvest due to storage shortage and fall at peak harvest. "
            "If the farmer has safe storage, holding 2-4 weeks after harvest often improves price. "
            "Compare the forecast price trend, storage cost, and spoilage risk before selling. "
            "Distant markets may pay more but add transport cost — weigh net return."
        ),
    ),
    KnowledgeDoc(
        id="scheme-krishi-card",
        title="Agricultural input subsidy & Krishi Card",
        category="scheme",
        tags=["scheme", "subsidy", "কৃষি কার্ড", "credit", "loan"],
        text=(
            "The government runs input subsidy programs and the Krishak Card / agricultural credit "
            "for smallholders. Eligibility generally requires a farmer registration and land record. "
            "Credit terms depend on repayment history and production consistency. Contact the local "
            "DAE (Department of Agricultural Extension) office or upazila agriculture office."
        ),
    ),
    KnowledgeDoc(
        id="scheme-climate-fund",
        title="Climate / carbon incentive schemes",
        category="scheme",
        tags=["scheme", "carbon", "climate", "সustain"],
        text=(
            "Farmers adopting verified sustainable practices (compost, cover cropping, agroforestry, "
            "reduced tillage) may qualify for government green funds or carbon-credit partnerships. "
            "Eligibility depends on documented practices and a sustainability score; keep diary "
            "records as evidence."
        ),
    ),
    KnowledgeDoc(
        id="irrigation-schedule",
        title="Irrigation scheduling basics",
        category="agronomy",
        tags=["irrigation", "সেচ", "water", "et0", "schedule"],
        text=(
            "Schedule irrigation by crop water need, not by calendar. Reference evapotranspiration "
            "(ET0) and the crop coefficient (Kc) give crop water use. Irrigate when soil depletion "
            "exceeds 50% of available water (management allowable depletion). Rice needs continuous "
            "flooding; most vegetables need infrequent deep irrigation."
        ),
    ),
    KnowledgeDoc(
        id="soil-health-compost",
        title="Improving soil health with organic matter",
        category="agronomy",
        tags=["soil", "compost", "স্বাস্থ্য", "organic", "carbon"],
        text=(
            "Regular compost and vermicompost improve soil structure, water holding capacity, and "
            "microbial life. Aim to return crop residues and apply 2-5 t/ha compost per season where "
            "possible. Healthy soil reduces fertilizer need and buffers drought."
        ),
    ),
    KnowledgeDoc(
        id="pest-ipm",
        title="Integrated Pest Management (IPM)",
        category="pest",
        tags=["pest", "ipm", "পোকা", "management"],
        text=(
            "IPM combines resistant varieties, cultural practices, biological control, and judicious "
            "chemical use as a last resort. Scout fields weekly, use thresholds before spraying, and "
            "preserve natural enemies. This lowers cost and residue while sustaining yields."
        ),
    ),
    KnowledgeDoc(
        id="weather-advisory",
        title="Using weather in farm decisions",
        category="advisory",
        tags=["weather", "আবহাওয়া", "forecast", "rain"],
        text=(
            "Before spraying or irrigating, check the 3-7 day forecast. Avoid spraying if rain is "
            "expected within 24 hours (wash-off + runoff). Schedule irrigation ahead of dry spells. "
            "Heat and high humidity raise disease pressure — increase scouting then."
        ),
    ),
    KnowledgeDoc(
        id="yield-estimation",
        title="Estimating yield and planning",
        category="agronomy",
        tags=["yield", "ফলন", "planning", "season"],
        text=(
            "Yield depends on variety, weather, water, and management. Use historical farm yield as a "
            "strong baseline, adjust for current-season rainfall and pest pressure, and build a season "
            "plan with planting window, nutrition, and monitoring milestones."
        ),
    ),
    KnowledgeDoc(
        id="faq-water-stress",
        title="Signs of water stress in crops",
        category="faq",
        tags=["water", "সেচ", "stress", "faq"],
        text=(
            "Wilting during midday that recovers by evening, leaf rolling, and slowed growth indicate "
            "water deficit. Continuous flooding causes yellowing and root rot in non-rice crops. Match "
            "irrigation to the crop stage — flowering and grain-fill are most sensitive."
        ),
    ),
]
