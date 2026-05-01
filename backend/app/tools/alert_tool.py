from langchain.tools import BaseTool

class PestRiskTool(BaseTool):
    name: str = "Pest and Disease Risk Calculator"
    description: str = "Calculates the risk level for common pests/diseases based on weather conditions (temperature, humidity) and crop type."
    
    def _run(self, crop: str, temperature: float = 28.0, humidity: float = 75.0, **kwargs) -> str:
        # Rule-based pest risk predictor
        crop = str(crop).strip().lower()
        
        risk_level = "Low"
        warnings = []
        
        # Example rules for Bangladeshi crops
        if crop == "potato":
            if temperature > 10 and temperature < 25 and humidity >= 85:
                risk_level = "High"
                warnings.append("Late Blight (নাবি ধসা): High risk due to cool, highly humid conditions. Apply protective fungicide.")
        
        elif crop == "rice" or crop == "paddy":
            if temperature >= 25 and humidity >= 80:
                risk_level = "Medium"
                warnings.append("Brown Plant Hopper (কারেন্ট পোকা): Favorable conditions developing. Monitor the base of the rice plants.")
            if temperature > 30 and humidity < 70:
                risk_level = "Low"
                warnings.append("Rice Stem Borer (মাজরা পোকা): Normal risk, continue standard monitoring.")
                
        elif crop == "brinjal":
            if temperature > 25:
                risk_level = "High"
                warnings.append("Fruit and Shoot Borer (ডগা ও ফল ছিদ্রকারী পোকা): High risk in warm weather. Check for wilted shoots.")
        
        if not warnings:
            warnings.append(f"No specific pest alerts for {crop} under current weather conditions.")
            
        output = f"--- PEST RISK ASSESSMENT FOR {crop.upper()} ---\n"
        output += f"Current Weather: {temperature}°C, {humidity}% Humidity\n"
        output += f"Overall Risk Level: {risk_level}\n\n"
        output += "Alerts:\n"
        for w in warnings:
            output += f"- {w}\n"
            
        return output
