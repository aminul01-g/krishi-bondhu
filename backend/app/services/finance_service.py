import os
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db_models import FarmDiary

logger = logging.getLogger("FinanceService")

# --- NLP Category Detection ---

CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "seed": ["বীজ", "seed", "চারা", "সীড"],
    "fertilizer": ["সার", "fertilizer", "ইউরিয়া", "ডিএপি", "পটাশ", "টিএসপি"],
    "pesticide": ["কীটনাশক", "pesticide", "বিষ", "ওষুধ", "কীটনাশক", "ফাংগিসাইড"],
    "labor": ["মজুর", "labor", "শ্রমিক", "মজুরি", "কামলা", "labour"],
    "irrigation": ["সেচ", "irrigation", "পানি", "পাম্প", "নলকূপ"],
    "harvest": ["ফলন", "harvest", "বিক্রি", "আয়", "ফসল", "কাটা", "বিক্রয়"],
}


def detect_category(text: str) -> str:
    """
    Detects the agricultural category from a Bengali/English diary text.
    Returns the matched category key, or 'other' if none match.
    """
    if not text:
        return "other"
    text_lower = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                return category
    return "other"


class FinanceService:
    """
    Production-grade Service for agricultural finance, subsidies, and credit scoring.
    """
    def __init__(self):
        self.subsidy_data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'finance_data.json')

    def get_eligible_subsidies(self, crop: str = "All", land_size: float = 0.0) -> List[Dict[str, Any]]:
        """
        Filters government subsidies based on crop type and land size.
        """
        if not os.path.exists(self.subsidy_data_path):
            logger.error(f"Subsidy data file missing at {self.subsidy_data_path}")
            return []

        try:
            with open(self.subsidy_data_path, 'r', encoding='utf-8') as f:
                schemes = json.load(f)
        except Exception as e:
            logger.error(f"Error reading subsidy data: {e}")
            return []

        eligible = []
        for s in schemes:
            criteria = s.get("eligibility_criteria", {})
            min_land = float(criteria.get("min_land", 0.0))
            target_crops = criteria.get("crops", ["All"])

            if land_size >= min_land:
                if "All" in target_crops or crop.lower() in [c.lower() for c in target_crops]:
                    eligible.append(s)

        return eligible

    async def calculate_credit_score(self, session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """
        Calculates a 0-100 credit readiness score based on farm diary logs.

        Scoring metrics:
        - Consistency (40 pts): Logging frequency over past 90 days.
        - Profitability (30 pts): Ratio of total income to total expenses.
        - Completeness (30 pts): Percentage of entries with rich metadata.
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=90)
            stmt = select(FarmDiary).where(
                (FarmDiary.user_id == user_id) &
                (FarmDiary.date >= cutoff_date)
            ).order_by(FarmDiary.date)

            result = await session.execute(stmt)
            entries = result.scalars().all()

            if not entries:
                return {
                    "score": 0,
                    "breakdown": {"consistency": 0, "profitability": 0, "completeness": 0},
                    "recommendation": "নোটঃ কোনো ডায়েরি এন্ট্রি পাওয়া যায়নি। নিয়মিত এন্ট্রি যোগ করুন।"
                }

            # 1. Consistency (40 pts)
            days_tracked = (entries[-1].date - entries[0].date).days + 1 if len(entries) > 1 else 1
            weeks_tracked = max(days_tracked / 7, 1)
            avg_entries_per_week = len(entries) / weeks_tracked
            consistency_score = min(40, int(avg_entries_per_week * 10))

            # 2. Profitability (30 pts)
            total_income = sum(e.amount for e in entries if e.entry_type == "income")
            total_expense = sum(e.amount for e in entries if e.entry_type == "expense")

            if total_expense == 0:
                profitability_score = 30
            else:
                profit_ratio = total_income / total_expense
                if profit_ratio >= 1.2: profitability_score = 30
                elif profit_ratio >= 1.0: profitability_score = 20
                elif profit_ratio >= 0.8: profitability_score = 10
                else: profitability_score = 0

            # 3. Completeness (30 pts)
            complete_entries = sum(1 for e in entries if e.crop and e.plot and e.notes and len(str(e.notes).strip()) > 5)
            completeness_score = int((complete_entries / len(entries)) * 30)

            total_score = consistency_score + profitability_score + completeness_score

            # Recommendation Mapping
            if total_score >= 80: rec = "চমৎকার! আপনি সহজেই কৃষি ঋণের জন্য আবেদন করতে পারেন।"
            elif total_score >= 60: rec = "ভালো ফলাফল। আরও কিছু মাস নিয়মিত রেকর্ড রাখলে স্কোর আরও বাড়বে।"
            elif total_score >= 40: rec = "সন্তোষজনক, তবে প্রতি সপ্তাহে অন্তত ২ টি বিস্তারিত এন্ট্রি যোগ করুন।"
            else: rec = "আপনার রেকর্ড এখনো দুর্বল। নিয়মিত ডায়েরি লিখুন।"

            return {
                "score": total_score,
                "breakdown": {
                    "consistency": consistency_score,
                    "profitability": profitability_score,
                    "completeness": completeness_score
                },
                "recommendation": rec
            }
        except Exception as e:
            logger.error(f"Credit scoring failed: {e}")
            return {"error": "Internal scoring error", "score": 0}

    def get_insurance_quote(
        self,
        crop: str,
        land_size: float,
        region_risk: str = "moderate",
        historical_loss_ratio: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Weather-indexed insurance quote with risk-based pricing.

        Premium is not a flat 5%: it scales with the crop's yield-volatility risk
        class, the region's climate exposure, and the farmer's historical loss
        ratio. Returns the premium drivers so the quote is explainable.
        """
        crop_l = (crop or "").lower()
        crop_risk_class = {
            "rice": "moderate", "ধান": "moderate", "paddy": "moderate",
            "wheat": "low", "গম": "low",
            "potato": "moderate", "আলু": "moderate",
            "onion": "high", "পেঁয়াজ": "high",
            "tomato": "high", "টমেটো": "high",
            "brinjal": "moderate", "বেগুন": "moderate",
            "chili": "high", "মরিচ": "high",
            "mango": "moderate", "আম": "moderate",
            "jute": "low", "পাট": "low",
        }.get(crop_l, "moderate")

        risk_multiplier = {"low": 0.8, "moderate": 1.0, "high": 1.4}[crop_risk_class]
        region_multiplier = {"low": 0.85, "moderate": 1.0, "high": 1.3}.get(region_risk, 1.0)
        loss_multiplier = 1.0 + min(0.5, max(0.0, historical_loss_ratio))

        sum_insured_per_bigha = 400 if crop_risk_class == "low" else 500
        sum_insured = land_size * sum_insured_per_bigha
        # Base premium rate 4% of sum insured, scaled by risk factors.
        base_rate = 0.04
        premium_rate = round(base_rate * risk_multiplier * region_multiplier * loss_multiplier, 4)
        premium = round(sum_insured * premium_rate, 2)
        payout_max = round(sum_insured, 2)

        return {
            "crop": crop,
            "land_size": land_size,
            "crop_risk_class": crop_risk_class,
            "region_risk": region_risk,
            "sum_insured": payout_max,
            "premium_rate": premium_rate,
            "premium": premium,
            "payout_max": payout_max,
            "premium_drivers": {
                "crop_risk_class": crop_risk_class,
                "region_multiplier": region_multiplier,
                "loss_multiplier": round(loss_multiplier, 3),
            },
            "triggers": [
                "টানা ১৫ দিন বৃষ্টি না হলে (খরা)",
                "এক দিনে ১০০ মি.মি. এর বেশি বৃষ্টি হলে (অতিবৃষ্টি)",
                "ঝড়ে ফসলের ৫০% এর বেশি ক্ষতি হলে"
            ],
        }

    def simulate_payout(
        self, crop: str, land_size: float, scenario: str = "drought",
        severity: float = 0.5, region_risk: str = "moderate",
    ) -> Dict[str, Any]:
        """Estimate the payout for a given weather scenario and severity (0..1)."""
        quote = self.get_insurance_quote(crop, land_size, region_risk=region_risk)
        # Payout scales with severity of the triggered peril, capped at sum insured.
        payout = round(min(quote["payout_max"], quote["payout_max"] * severity), 2)
        return {
            "scenario": scenario,
            "severity": severity,
            "estimated_payout": payout,
            "sum_insured": quote["payout_max"],
            "net_after_premium": round(payout - quote["premium"], 2),
        }
