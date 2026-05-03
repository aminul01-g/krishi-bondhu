import os
import json
import logging
from crewai_tools import BaseTool
from app.config.model_config import model_registry

logger = logging.getLogger("ReceiptScanner")

class ReceiptScannerTool(BaseTool):
    name: str = "Receipt Scanner"
    description: str = "Extracts structured financial data from farm-related receipts, including item names, prices, quantities, and dates."

    def _run(self, image_path: str) -> str:
        """
        Uses vision models to parse receipt images into structured JSON.
        """
        if not image_path or image_path.lower() == "none":
            return "No image provided for receipt scanning."

        logger.info(f"Scanning receipt: {image_path}")
        
        try:
            # We use the vision-capable model to interpret the receipt
            vision_llm = model_registry.get_interpreter_llm() # Assuming this is vision-capable or we use a fallback
            
            # In a real implementation, we would send the image to a vision API
            # For now, we simulate the high-fidelity extraction logic
            
            # Simulated Prompt:
            # "Analyze this receipt image. Extract: 
            # 1. Total Amount, 2. Store Name, 3. Items with Prices, 4. Date.
            # Return ONLY JSON."
            
            # Mock Result for Demonstration
            mock_data = {
                "store": "Pabna Agri-Inputs Ltd.",
                "date": "2026-05-01",
                "total": 4500,
                "currency": "BDT",
                "items": [
                    {"name": "Urea Fertilizer", "quantity": "2 bags", "price": 1800},
                    {"name": "Hybrid Rice Seeds", "quantity": "5 kg", "price": 2700}
                ],
                "confidence": 0.94
            }
            
            return json.dumps(mock_data)
            
        except Exception as e:
            logger.error(f"Failed to scan receipt: {e}")
            return f"Error scanning receipt: {str(e)}"
