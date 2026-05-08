from langchain.tools import BaseTool
from pydantic import Field
from PIL import Image
import os
import logging

logger = logging.getLogger("VisionTool")


class LocalVisionDiseaseTool(BaseTool):
    name: str = "Local Image Disease Analyzer"
    description: str = "Analyzes an image of a crop to detect diseases using a 3-tier vision pipeline: HuggingFace ViT → Groq Vision → rule engine."

    # In a production environment, you would load this model once in the factory or app startup.
    # We initialize it here for demonstration.
    def _run(self, image_path: str, **kwargs) -> str:
        if not image_path or image_path.lower() == "none" or not os.path.exists(image_path):
            return "No valid image provided to analyze."

        from app.services.vision_service import VisionService

        svc = VisionService()
        result = svc.analyze_image(image_path, task="disease")

        # Append guidance for the downstream agent
        return f"{result}\n\nPlease use this data to formulate a farmer-friendly diagnosis and treatment plan."
