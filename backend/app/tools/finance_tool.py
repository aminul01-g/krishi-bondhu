from langchain.tools import BaseTool
import json
import os
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, func
import asyncio

logger = logging.getLogger("FinanceTools")

class SubsidyNavigatorTool(BaseTool):
    name: str = "Subsidy & Scheme Navigator"
    description: str = "Finds eligible government subsidies and provides step-by-step 'How to Apply' guides in Bengali."
    
    def _run(self, crop: str = "All", land_size: float = 0.0) -> str:
        data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'finance_data.json')
        if not os.path.exists(data_path):
            return "Subsidy data unavailable."
            
        with open(data_path, 'r', encoding='utf-8') as f:
            schemes = json.load(f)
            
        eligible = []
        for s in schemes:
            criteria = s.get("eligibility_criteria", {})
            # Ensure min_land is float and handle comparison safely
            min_land = float(criteria.get("min_land", 0.0))
            land_size_f = float(land_size)
            target_crops = criteria.get("crops", ["All"])
            
            # Check eligibility
            if land_size_f >= min_land:
                if "All" in target_crops or crop.lower() in [c.lower() for c in target_crops]:
                    eligible.append(s)
                    
        if not eligible:
            return "দুঃখিত, আপনার দেওয়া তথ্যের ভিত্তিতে এই মুহূর্তে কোনো উপযুক্ত সরকারি স্কিম পাওয়া যায়নি।"
            
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
        # In a real tool with DB access, we would run the query here.
        # Since tools are sync and our DB is async, we'll use a helper to run the async query.
        
        # MOCK LOGIC FOR PROTOTYPE
        # In a production version, we would fetch data from 'farm_diary' table.
        # Here we simulate the scoring based on a mock check.
        
        # points = 0
        # 1. Consistency (Weekly logging) -> 40 pts
        # 2. Profitability (Income > Expense) -> 30 pts
        # 3. Completeness (Notes/Metadata) -> 30 pts
        
        score = 75 # Mock score
        breakdown = (
            "- তথ্যের ধারাবাহিকতা: ২৫/৪০ (গত মাসে ৩ সপ্তাহ লগ করেছেন)\n"
            "- লাভজনকতা: ৩০/৩০ (আপনার আয় ব্যয়ের চেয়ে বেশি)\n"
            "- তথ্যের পূর্ণতা: ২০/৩০ (কিছু এন্ট্রিতে নোট যুক্ত করা হয়নি)"
        )
        
        output = f"আপনার ক্রেডিট রেডিনেস স্কোর: {score}/১০০\n\n"
        output += "বিশ্লেষণ:\n"
        output += breakdown + "\n\n"
        
        if score >= 80:
            output += "পরামর্শ: আপনার রেকর্ড খুবই ভালো। আপনি কৃষি ঋণের জন্য ব্যাংকে আবেদন করতে পারেন।"
        elif score >= 50:
            output += "পরামর্শ: ঋণের জন্য আপনার রেকর্ড সন্তোষজনক। তবে আরও নিয়মিত তথ্য যোগ করলে ভালো হয়।"
        else:
            output += "পরামর্শ: ঋণের আবেদন করার আগে নিয়মিত অন্তত ৩ মাস আপনার আয়-ব্যয় ডায়েরিতে লিখে রাখুন।"
            
        return output

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
        
        output = f"--- আবহাওয়া ভিত্তিক বীমা উদ্ধৃতি ({crop}) ---\n"
        output += f"জমির পরিমাণ: {land_size} শতাংশ\n"
        output += f"সম্ভাব্য প্রিমিয়াম: {premium} টাকা\n"
        output += f"সর্বোচ্চ ক্ষতিপূরণ: {payout_max} টাকা\n\n"
        output += "ক্ষতিপূরণের শর্তসমূহ (Payout Triggers):\n"
        output += "- টানা ১৫ দিন বৃষ্টি না হলে (খরা)।\n"
        output += "- এক দিনে ১০০ মি.মি. এর বেশি বৃষ্টি হলে (অতিবৃষ্টি)।\n"
        output += "- ঝড়ে ফসলের ৫০% এর বেশি ক্ষতি হলে।"
        
        return output
