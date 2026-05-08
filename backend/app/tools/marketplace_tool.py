from crewai_tools import BaseTool
import httpx
import base64
import os
try:
    import cv2
    import pytesseract
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

class DealerSearchTool(BaseTool):
    name: str = "Search Local Dealers"
    description: str = "Find nearby verified dealers for specific inputs like 'seeds' or 'fertilizer'. Requires lat and lon."

    def _run(self, input_type: str = "general", lat: float = None, lon: float = None, gps: str = None, **kwargs) -> str:
        # Robust GPS parsing
        if gps and (not lat or not lon):
            try:
                import re
                nums = re.findall(r"[-+]?\d*\.\d+|\d+", str(gps))
                if len(nums) >= 2:
                    lat, lon = float(nums[0]), float(nums[1])
            except Exception:
                pass
                
        # Default to Dhaka if still missing
        lat = lat or 23.81
        lon = lon or 90.41
        try:
            with httpx.Client() as client:
                response = client.get("http://localhost:8000/api/marketplace/dealers", params={"lat": float(lat), "lon": float(lon), "limit": 3})
                if response.status_code == 200:
                    results = response.json()
                    if not results:
                        return f"No dealers found near this location for {input_type}."
                    
                    formatted = []
                    for r in results:
                        # Assuming the API returns 'name' and 'distance'
                        dist = r.get('distance', 'Unknown')
                        formatted.append(f"- {r.get('name', 'Dealer')} ({dist} away). Contact: {r.get('phone_number', 'N/A')}")
                    return f"Found nearby dealers for {input_type}:\n" + "\n".join(formatted)
                return f"Failed to search: API returned {response.status_code}"
        except Exception as e:
            return f"Error searching for dealers: {str(e)}"

class BarcodeVerificationTool(BaseTool):
    name: str = "Verify Product Barcode"
    description: str = "Verify a product's authenticity by its barcode or QR code image. Pass the image_path."

    def _run(self, image_path: str, farmer_id: str = "farmer_123") -> str:
        if not os.path.exists(image_path):
            return f"Error: Image file not found at {image_path}"

        try:
            import base64
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

            from app.services.barcode_service import decode_barcode_base64
            barcode = decode_barcode_base64(encoded_string)

            if not barcode:
                return "No barcode or QR code could be detected in the image. Please try a clearer, better-lit photo."

            with httpx.Client() as client:
                payload = {
                    "farmer_id_hashed": farmer_id,
                    "barcode": barcode
                }
                response = client.post("http://localhost:8000/api/marketplace/scan", json=payload)
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("verification_status", "unknown")
                    if status == "verified":
                        return f"STATUS GREEN: Product {data.get('product_name', '')} (Barcode: {barcode}) is verified and authentic."
                    elif status == "suspicious":
                        return f"STATUS YELLOW: Barcode {barcode} not found in the verified database. Use caution."
                    else:
                        return f"STATUS RED: Counterfeit warning for barcode {barcode}. Do not purchase."
                return f"Failed to verify: API returned {response.status_code}"
        except Exception as e:
            return f"Error verifying barcode: {str(e)}"

class ProductVerificationTool(BaseTool):
    name: str = "Verify Product by Barcode Text"
    description: str = "Verify a product's authenticity using a known barcode string."


class LabelScannerTool(BaseTool):
    name: str = "Scan Label with OCR"
    description: str = "Extract text from an image of a pesticide or fertilizer label to find active ingredients. Pass the image_path."

    def _run(self, image_path: str) -> str:
        if not os.path.exists(image_path):
            return f"Error: Image file not found at {image_path}"

        try:
            # Read image as base64 to use the service's existing interface
            import base64
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

            from app.services.ocr_service import extract_text_from_base64, parse_label_text
            raw_text = extract_text_from_base64(encoded_string)
            parsed = parse_label_text(raw_text)

            return (
                f"OCR Analysis Results:\n"
                f"- Product: {parsed['product_name']}\n"
                f"- Active Ingredient: {parsed['active_ingredient']}\n"
                f"- NPK Ratio: {parsed['npk_ratio']}\n"
                f"- Expiry: {parsed['expiry']}\n"
                f"- Dosage: {parsed['dose']}\n"
                f"- Raw Text Snippet: {raw_text[:200]}..."
            )
        except Exception as e:
            return f"OCR Error: {str(e)}. Please try a clearer photo of the label."
class ArbitrageAlertTool(BaseTool):
    name: str = "Price Arbitrage Scanner"
    description: str = "Compare crop prices across neighboring districts to identify transport-profitable opportunities."

    def _run(self, crop: str = "potato", current_district: str = "pabna") -> str:
        # Mock Price Database for regional spreads
        spreads = {
            "potato": [
                {"district": "Bogura", "price": 18, "dist": 40},
                {"district": "Rajshahi", "price": 24, "dist": 60},
                {"district": "Dhaka", "price": 32, "dist": 150}
            ],
            "rice": [
                {"district": "Dinajpur", "price": 45, "dist": 120},
                {"district": "Naogaon", "price": 42, "dist": 80}
            ]
        }
        
        current_price = 20 # Mock base price in current_district
        crop_lower = crop.lower()
        if crop_lower not in spreads:
            return f"No arbitrage data available for {crop}."
        
        opportunities = []
        for opp in spreads[crop_lower]:
            profit = opp['price'] - current_price
            if profit > 5: # Threshold for arbitrage
                opportunities.append(f"- {opp['district']}: {opp['price']} BDT (Spread: +{profit} BDT). Distance: {opp['dist']}km.")
        
        if not opportunities:
            return f"Local prices for {crop} are currently competitive. Transport not advised."
        
        return f"💡 ARBITRAGE ALERT for {crop}:\nPrices are significantly higher in neighboring markets:\n" + "\n".join(opportunities) + "\n\nConsider local transport if cost < 3 BDT/kg."
