from langchain.tools import BaseTool
from pydantic import Field

class WeatherLookupTool(BaseTool):
    name: str = "Weather and GPS Lookup Tool"
    description: str = "Fetches local weather and environmental data based on GPS coordinates."
    
    def _run(self, gps_coordinates: str, **kwargs) -> str:
        if not gps_coordinates or gps_coordinates.lower() == "none":
            return "No GPS coordinates provided. Assuming general tropical climate for Bangladesh."
            
        # Placeholder for an actual OpenWeatherMap or similar API call
        return (f"Weather data retrieved for {gps_coordinates}: "
                f"Temperature is 32°C, Humidity is 85%, Chance of rain is 60%. "
                f"Conditions are favorable for fungal diseases.")
