from datetime import datetime, timedelta
import math

class AgronomyService:
    @staticmethod
    def calculate_gdd(base_temp, min_temp, max_temp):
        """Calculates Growing Degree Days (GDD) for a single day."""
        avg_temp = (max_temp + min_temp) / 2
        return max(avg_temp - base_temp, 0)

    @staticmethod
    def predict_growth_stage(crop_name, planting_date, history_temps):
        """
        Predicts the current growth stage based on accumulated GDD.
        Mock logic for demonstration.
        """
        if not planting_date:
            return "Unknown (No planting date)"
            
        days_since_planting = (datetime.now() - planting_date).days
        
        # Mock stages for Rice
        if "rice" in crop_name.lower():
            if days_since_planting < 10: return "Germination"
            if days_since_planting < 30: return "Seedling/Tillering"
            if days_since_planting < 60: return "Stem Elongation"
            if days_since_planting < 90: return "Panicle Initiation"
            if days_since_planting < 110: return "Flowering/Heading"
            return "Ripening/Harvest"
            
        # Default simple model
        if days_since_planting < 15: return "Initial"
        if days_since_planting < 45: return "Development"
        if days_since_planting < 80: return "Mid-Season"
        return "Late-Season"

    @staticmethod
    def evaluate_risk(current_conditions, historical_facts):
        """
        Evaluates risk factors (Disease, Drought, Pests).
        """
        risks = []
        
        # Mock logic
        temp = current_conditions.get("temp", 30)
        humidity = current_conditions.get("humidity", 80)
        moisture = current_conditions.get("moisture", 20)
        
        if humidity > 85 and temp > 25:
            risks.append({"type": "Disease", "factor": "Fungal Blight", "level": "High"})
            
        if moisture < 15:
            risks.append({"type": "Environmental", "factor": "Drought Stress", "level": "Medium"})
            
        # Check if locusts reported in district
        district = next((f.value for f in historical_facts if f.key == "district"), "Pabna")
        if district == "Pabna":
            risks.append({"type": "Pest", "factor": "Regional Locust Alert", "level": "High"})
            
        return risks
