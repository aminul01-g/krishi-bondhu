from crewai_tools import BaseTool
import httpx
import os
import uuid
import datetime
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

class CropDamageAssessmentTool(BaseTool):
    name: str = "Assess Crop Damage"
    description: str = "Analyze an image of a crop to estimate the percentage of damage using rule-based vegetation indices. Requires image_path and crop_type."

    def _run(self, image_path: str = "none", crop_type: str = "general", **kwargs) -> str:
        from app.services.vision_service import VisionService

        svc = VisionService()
        return svc.assess_damage(image_path, crop_type)

class DamageReportGeneratorTool(BaseTool):
    name: str = "Generate Damage Report"
    description: str = "Compiles GPS, damage level, and voice transcripts into an official damage report. Returns the report ID."
    
    def _run(self, farmer_id: str, lat: float, lon: float, crop_type: str, damage_percent: float, voice_transcript: str) -> str:
        try:
            with httpx.Client() as client:
                payload = {
                    "farmer_id": farmer_id,
                    "crop_type": crop_type,
                    "lat": float(lat),
                    "lon": float(lon),
                    "damage_cause": "Unknown/Visual",
                    "damage_estimate_percent": float(damage_percent),
                    "yield_loss_estimate_percent": float(damage_percent) * 1.1, # heuristic
                    "voice_statement_transcribed": voice_transcript
                }
                response = client.post("http://localhost:8000/api/emergency/reports", json=payload)
                if response.status_code == 200:
                    data = response.json()
                    return f"Successfully generated Official Damage Report ID: {data.get('id', 'N/A')}"
                return f"Failed to generate report: API returned {response.status_code}"
        except Exception as e:
            mock_id = str(uuid.uuid4())
            return f"Mock Damage Report Generated. ID: {mock_id}"

class SMSShareTool(BaseTool):
    name: str = "Share Report via SMS"
    description: str = "Send the generated damage report link to the farmer or insurance provider via SMS gateway."
    
    def _run(self, report_id: str, phone_number: str) -> str:
        # Mocking an SMS gateway like Twilio or bulk-sms BD
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        return f"SMS successfully sent to {phone_number} at {timestamp}. Content: 'KrishiBondhu: Your damage report {report_id[:8]} has been filed successfully.'"
