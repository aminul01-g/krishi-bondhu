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

    def get_insurance_quote(self, crop: str, land_size: float) -> Dict[str, Any]:
        """
        Calculates weather-indexed insurance quotes.
        """
        base_rate = 400 if "rice" in crop.lower() or "ধান" in crop else 500
        premium = round(land_size * base_rate * 0.05, 2)
        payout_max = land_size * base_rate * 10

        return {
            "crop": crop,
            "land_size": land_size,
            "premium": premium,
            "payout_max": payout_max,
            "triggers": [
                "টানা ১৫ দিন বৃষ্টি না হলে (খরা)",
                "এক দিনে ১০০ মি.মি. এর বেশি বৃষ্টি হলে (অতিবৃষ্টি)",
                "ঝড়ে ফসলের ৫০% এর বেশি ক্ষতি হলে"
            ]
        }
