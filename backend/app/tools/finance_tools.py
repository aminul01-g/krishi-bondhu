from langchain.tools import BaseTool
from app.services.finance_service import FinanceService
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Optional

class SubsidyNavigatorTool(BaseTool):
    name: str = "Subsidy & Scheme Navigator"
    description: str = "Finds eligible government subsidies and provides application guides."

    @property
    def service(self) -> FinanceService:
        return FinanceService()

    def _run(self, crop: str = "All", land_size: float = 0.0, **kwargs) -> str:
        eligible = self.service.get_eligible_subsidies(crop, land_size)
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
    description: str = "Calculates a 0-100 credit readiness score based on farm diary logs."

    @property
    def service(self) -> FinanceService:
        return FinanceService()

    def _run(self, user_id: str, **kwargs) -> str:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        async def execute():
            from app.db import AsyncSessionLocal
            async with AsyncSessionLocal() as session:
                data = await self.service.calculate_credit_score(session, user_id)
                if "error" in data:
                    return f"Error: {data['error']}"

                res = f"### CREDIT READINESS SCORE: {data['score']}/100\n\n"
                res += f"Breakdown:\n"
                res += f"- Consistency: {data['breakdown']['consistency']}/40\n"
                res += f"- Profitability: {data['breakdown']['profitability']}/30\n"
                res += f"- Completeness: {data['breakdown']['completeness']}/30\n\n"
                res += f"Recommendation: {data['recommendation']}\n"
                return res

        return loop.run_until_complete(execute())

class InsuranceQuoteTool(BaseTool):
    name: str = "Micro-Insurance Quoter"
    description: str = "Provides weather-indexed crop insurance quotes and payout trigger details."

    @property
    def service(self) -> FinanceService:
        return FinanceService()

    def _run(self, crop: str, land_size: float, **kwargs) -> str:
        quote = self.service.get_insurance_quote(crop, land_size)
        output = f"--- আবহাওয়া ভিত্তিক বীমা উদ্ধৃতি ({quote['crop']}) ---\n"
        output += f"জমির পরিমাণ: {quote['land_size']} শতাংশ\n"
        output += f"সম্ভাব্য প্রিমিয়াম: {quote['premium']} টাকা\n"
        output += f"সর্বোচ্চ ক্ষতিপূরণ: {quote['payout_max']} টাকা\n\n"
        output += "ক্ষতিপূরণের শর্তসমূহ (Payout Triggers):\n"
        output += "• " + "\n• ".join(quote['triggers'])
        return output
