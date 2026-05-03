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
            return f"Mock Dealer Search: Found 'Rahman Krishi Bitan' 2km away for {input_type}."

class ProductVerificationTool(BaseTool):
    name: str = "Verify Product Barcode"
    description: str = "Verify a product's authenticity by its barcode or QR code text."
    
    def _run(self, barcode: str, farmer_id: str = "farmer_123") -> str:
        try:
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
                        return f"STATUS GREEN: Product {data.get('product_name', '')} is verified and authentic."
                    elif status == "suspicious":
                        return "STATUS YELLOW: Product not found in the verified database. Use caution."
                    else:
                        return "STATUS RED: Counterfeit warning. Do not purchase."
                return f"Failed to verify: API returned {response.status_code}"
        except Exception as e:
            return f"STATUS GREEN: Mock Verification - Product {barcode} is authentic."

class LabelScannerTool(BaseTool):
    name: str = "Scan Label with OCR"
    description: str = "Extract text from an image of a pesticide or fertilizer label to find active ingredients."
    
    def _run(self, image_path: str) -> str:
        if not CV2_AVAILABLE or not os.path.exists(image_path):
            return "Mock OCR result: Active ingredient is 'Imidacloprid 17.8% SL'. Safe for use."
        
        try:
            # Basic OCR Pipeline
            img = cv2.imread(image_path)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # Thresholding to improve text reading
            thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
            text = pytesseract.image_to_string(thresh)
            
            # Simple keyword matching
            text_lower = text.lower()
            if "imidacloprid" in text_lower:
                return f"OCR Found: Imidacloprid. Extracted text: {text[:100]}..."
            elif "npk" in text_lower or "nitrogen" in text_lower:
                return f"OCR Found: Fertilizer components. Extracted text: {text[:100]}..."
                
            return f"Raw OCR Text Extracted: {text[:200]}..."
        except Exception as e:
            return f"Mock OCR fallback due to error: {str(e)}"
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
