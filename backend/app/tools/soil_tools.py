from langchain.tools import BaseTool
from app.services.soil_service import SoilService
from typing import Any, Optional

class SoilVisionTool(BaseTool):
    name: str = "Soil Image Analyzer"
    description: str = "Analyzes an image of soil to estimate texture and organic matter."

    @property
    def service(self) -> SoilService:
        return SoilService()

    def _run(self, image_path: str, **kwargs) -> str:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.service.analyze_soil_image(image_path))

class DIYSoilTestTool(BaseTool):
    name: str = "DIY Soil Test Interpreter"
    description: str = "Interprets physical DIY soil tests (Ribbon/pH/Jar tests)."

    @property
    def service(self) -> SoilService:
        return SoilService()

    def _run(self, test_data_json: str, **kwargs) -> str:
        return self.service.interpret_diy_test(test_data_json)

class RecommendFertilizerTool(BaseTool):
    name: str = "Balanced Fertilizer Recommender"
    description: str = "Generates fertilizer plans based on soil data and crop."

    @property
    def service(self) -> SoilService:
        return SoilService()

    def _run(self, soil_summary: str, crop: str, **kwargs) -> str:
        return self.service.recommend_fertilizer(soil_summary, crop)
