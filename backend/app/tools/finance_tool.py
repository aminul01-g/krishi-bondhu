from langchain.tools import BaseTool
import json
import os
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db_models import FarmDiary
import asyncio

logger = logging.getLogger("FinanceTools")

class SubsidyNavigatorTool(BaseTool):
    name: str = "Subsidy & Scheme Navigator"
    description: str = "Finds eligible government subsidies and provides step-by-step 'How to Apply' guides in Bengali."
    
    def _run(self, crop: str = "All", land_size: str = "0.0") -> str:
        data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'finance_data.json')
        if not os.path.exists(data_path):
            return "Subsidy data unavailable."
            
        with open(data_path, 'r', encoding='utf-8') as f:
            schemes = json.load(f)
            
        try:
            # Handle cases where land_size might have units like 'acres'
            import re
            numeric_match = re.search(r"[-+]?\d*\.\d+|\d+", str(land_size))
            land_size_f = float(numeric_match.group()) if numeric_match else 0.0
        except Exception:
            land_size_f = 0.0
            
        eligible = []
        for s in schemes:
            criteria = s.get("eligibility_criteria", {})
            min_land = float(criteria.get("min_land", 0.0))
            target_crops = criteria.get("crops", ["All"])
            
            if land_size_f >= min_land:
                if "All" in target_crops or str(crop).lower() in [c.lower() for c in target_crops]:
                    eligible.append(s)
                    
        if not eligible:
            return "দুঃখিত, আপনার দেওয়া তথ্যের ভিত্তিতে এই মুহূর্তে কোনো উপযুক্ত সরকারি স্কিম পাওয়া যায়নি।"
            
        output = "আপনার জন্য প্রযোজ্য সরকারি স্কিমসমূহ:\n\n"
        for s in eligible:
            output += f"--- {s['name_bn']} ---\n"
            output += f"বিবরণ: {s['description_bn']}\n"
            output += f"আবেদন পদ্ধতি:\n{s['how_to_apply_bn']}\n"
            output += f"লিঙ্ক: {s['apply_link']}\n\n"
            
        return output

class CreditScoringTool(BaseTool):
    name: str = "Credit Readiness Scorer"
    description: str = "Calculates a 0-100 credit readiness score based on farm diary logs (consistency, profitability, completeness)."
    
    def _run(self, user_id: str) -> str:
        """Synchronous wrapper for credit scoring."""
        from app.db import AsyncSessionLocal
        import asyncio
        
        async def run_scoring():
            async with AsyncSessionLocal() as session:
                return await self.calculate_credit_score(session, user_id)
        
        def run_sync():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                return loop.run_until_complete(run_scoring())
            finally:
                loop.close()
        
        try:
            data = run_sync()
            
            if not data or "error" in data:
                return f"Error: {data.get('error', 'Unknown error during scoring')}"
                
            res = f"### CREDIT READINESS SCORE: {data['score']}/100\n\n"
            res += f"Breakdown:\n"
            res += f"- Consistency: {data['breakdown']['consistency']}/40\n"
            res += f"- Profitability: {data['breakdown']['profitability']}/30\n"
            res += f"- Completeness: {data['breakdown']['completeness']}/30\n\n"
            res += f"Recommendation: {data['recommendation']}\n"
            return res
        except Exception as e:
            return f"Unable to calculate credit score at this time: {str(e)}"
    
    async def calculate_credit_score(self, session: AsyncSession, user_id: str) -> dict:
        """
        Real credit scoring logic based on farm diary data.
        
        Scoring breakdown:
        - Consistency (40 pts): Weekly logging frequency over past 90 days
        - Profitability (30 pts): Ratio of total income to total expenses
        - Completeness (30 pts): Percentage of entries with notes/crop/plot data
        """
        try:
            # Fetch all diary entries for the user in past 90 days
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
                    "breakdown": {
                        "consistency": 0,
                        "profitability": 0,
                        "completeness": 0
                    },
                    "message": "নোটঃ কোনো ডায়েরি এন্ট্রি পাওয়া যায়নি। অন্তত ২ সপ্তাহ নিয়মিত এন্ট্রি যোগ করলে আপনার ক্রেডিট স্কোর গণনা করা যাবে।"
                }
            
            # 1. CONSISTENCY SCORING (40 pts)
            # Calculate logging frequency - aim for 2+ entries per week = 40 pts
            days_tracked = (entries[-1].date - entries[0].date).days + 1 if len(entries) > 1 else 1
            weeks_tracked = max(days_tracked / 7, 1)
            avg_entries_per_week = len(entries) / weeks_tracked
            consistency_score = min(40, int(avg_entries_per_week * 10))  # Max 40 pts
            
            # 2. PROFITABILITY SCORING (30 pts)
            total_income = 0
            total_expense = 0
            for entry in entries:
                if entry.entry_type == "income":
                    total_income += entry.amount
                elif entry.entry_type == "expense":
                    total_expense += entry.amount
            
            if total_expense == 0:
                profitability_score = 30  # If no expenses logged, full score
            else:
                profit_ratio = total_income / total_expense if total_expense > 0 else 0
                if profit_ratio >= 1.2:  # 20%+ profit = full score
                    profitability_score = 30
                elif profit_ratio >= 1.0:  # Break-even or slight profit
                    profitability_score = 20
                elif profit_ratio >= 0.8:  # Up to 20% loss
                    profitability_score = 10
                else:  # More than 20% loss
                    profitability_score = 0
            
            # 3. COMPLETENESS SCORING (30 pts)
            complete_entries = sum(
                1 for e in entries
                if e.crop and e.plot and e.notes and len(str(e.notes).strip()) > 5
            )
            completeness_score = int((complete_entries / len(entries)) * 30) if entries else 0
            
            # Total score
            total_score = consistency_score + profitability_score + completeness_score
            
            # Generate recommendation
            if total_score >= 80:
                recommendation = "চমৎকার! আপনার কৃষি ব্যবসা ভালো পথে চলছে। আপনি সহজেই কৃষি ঋণের জন্য ব্যাংকে আবেদন করতে পারেন।"
            elif total_score >= 60:
                recommendation = "ভালো ফলাফল। আরও ৩-৪ মাস নিয়মিত ডায়েরি রেখে আপনার স্কোর উন্নত করতে পারেন। তার পর ঋণের আবেদন করুন।"
            elif total_score >= 40:
                recommendation = "আপনার ডায়েরি রেকর্ড সন্তোষজনক কিন্তু আরও উন্নতির সুযোগ আছে। প্রতি সপ্তাহে অন্তত ২টি এন্ট্রি যোগ করুন এবং সব এন্ট্রিতে বিস্তারিত নোট লিখুন।"
            else:
                recommendation = "আপনার ডায়েরি রেকর্ড এখনো খুব দুর্বল। অন্তত ৬ মাস নিয়মিত দৈনিক/সাপ্তাহিক এন্ট্রি যোগ করুন তার পর ঋণের আবেদন করুন।"
            
            return {
                "score": total_score,
                "breakdown": {
                    "consistency": consistency_score,
                    "profitability": profitability_score,
                    "completeness": completeness_score
                },
                "metrics": {
                    "total_income": total_income,
                    "total_expense": total_expense,
                    "net_profit": total_income - total_expense,
                    "entries_count": len(entries),
                    "avg_entries_per_week": round(avg_entries_per_week, 2)
                },
                "recommendation": recommendation
            }
        
        except Exception as e:
            logger.error(f"Error calculating credit score: {e}")
            return {
                "score": 0,
                "error": str(e),
                "message": "ক্রেডিট স্কোর গণনা করতে সমস্যা হয়েছে। পরে আবার চেষ্টা করুন।"
            }

class InsuranceQuoteTool(BaseTool):
    name: str = "Micro-Insurance Quoter"
    description: str = "Provides weather-indexed crop insurance quotes and payout trigger details."
    
    def _run(self, crop: str, land_size: float) -> str:
        # Mock calculation logic
        # Premium is roughly 2-5% of estimated yield value
        base_rate = 500 # BDT per decimal of land
        if "rice" in crop.lower() or "ধান" in crop:
            base_rate = 400
            
        premium = round(land_size * base_rate * 0.05, 2)
        payout_max = land_size * base_rate * 10
        
        output = f"--- আবহাওয়া ভিত্তিক বীমা উদ্ধৃতি ({crop}) ---\n"
        output += f"জমির পরিমাণ: {land_size} শতাংশ\n"
        output += f"সম্ভাব্য প্রিমিয়াম: {premium} টাকা\n"
        output += f"সর্বোচ্চ ক্ষতিপূরণ: {payout_max} টাকা\n\n"
        output += "ক্ষতিপূরণের শর্তসমূহ (Payout Triggers):\n"
        output += "- টানা ১৫ দিন বৃষ্টি না হলে (খরা)।\n"
        output += "- এক দিনে ১০০ মি.মি. এর বেশি বৃষ্টি হলে (অতিবৃষ্টি)।\n"
        output += "- ঝড়ে ফসলের ৫০% এর বেশি ক্ষতি হলে।"
        
        return output
