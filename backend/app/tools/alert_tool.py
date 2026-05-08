from langchain.tools import BaseTool
from app.services.alert_service import AlertService
from typing import Any, Optional

class PestRiskTool(BaseTool):
    name: str = "Pest and Disease Risk Calculator"
    description: str = "Calculates the risk level for common pests/diseases based on current weather data and crop type."

    @property
    def service(self) -> AlertService:
        return AlertService()

    def _run(self, crop: str, lat: Optional[float] = None, lon: Optional[float] = None, **kwargs) -> str:
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        async def execute():
            # Use a default location if none provided
            lat = lat or 23.8103
            lon = lon or 90.4125
            risk_data = await self.service.calculate_pest_risk(crop, lat, lon)

            output = f"--- PEST RISK ASSESSMENT FOR {crop.upper()} ---\n"
            output += f"Current Weather: {risk_data['weather_context']['temp']}°C, {risk_data['weather_context']['humidity']}% Humidity\n"
            output += f"Overall Risk Level: {risk_data['risk_level']}\n\n"
            output += "Alerts:\n"
            for a in risk_data["alerts"]:
                output += f"- {a}\n"
            return output

        return loop.run_until_complete(execute())
