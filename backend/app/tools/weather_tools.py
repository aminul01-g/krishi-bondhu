from langchain.tools import BaseTool
from app.services.weather_service import WeatherService
from typing import Any, Optional

class WeatherLookupTool(BaseTool):
    name: str = "Weather and GPS Lookup Tool"
    description: str = "Fetches local weather and environmental data based on GPS coordinates."

    @property
    def service(self) -> WeatherService:
        return WeatherService()

    def _run(self, gps_coordinates: str, **kwargs) -> str:
        import asyncio

        # Expected format: "lat, lon"
        try:
            lat, lon = map(float, gps_coordinates.split(','))
        except (ValueError, AttributeError):
            return "Invalid GPS coordinates. Please provide in 'lat, lon' format."

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        async def execute():
            data = await self.service.get_weather_data(lat, lon)
            return f"Current Weather for {gps_coordinates}:\nTemp: {data['temp_mean']}°C, Humidity: {data['humidity']}%, Rainfall: {data['rainfall_mm']}mm."

        return loop.run_until_complete(execute())

class IrrigationAdvisorTool(BaseTool):
    name: str = "Precision Irrigation Advisor"
    description: str = "Calculates precise water needs using the Hargreaves-Samani equation and soil water balance."

    @property
    def service(self) -> WeatherService:
        return WeatherService()

    def _run(self, crop: str, gps_coordinates: str, **kwargs) -> str:
        import asyncio

        try:
            lat, lon = map(float, gps_coordinates.split(','))
        except (ValueError, AttributeError):
            return "Invalid GPS coordinates. Please provide in 'lat, lon' format."

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        async def execute():
            balance = await self.service.calculate_water_balance(crop, lat, lon)

            output = f"--- IRRIGATION ANALYSIS FOR {crop.upper()} ---\n"
            output += f"Reference ET0: {balance['et0']} mm/day\n"
            output += f"Crop ET: {balance['crop_evapotranspiration']} mm/day\n"
            output += f"Net Water Balance: {balance['net_water_balance']} mm\n"
            output += f"Status: {balance['status']}\n"

            if balance['status'] == "Deficit":
                output += f"Recommendation: Apply {balance['irrigation_recommendation_mm']} mm of water to maintain optimal growth."
            else:
                output += "Recommendation: No irrigation needed today; rainfall is sufficient."

            return output

        return loop.run_until_complete(execute())
