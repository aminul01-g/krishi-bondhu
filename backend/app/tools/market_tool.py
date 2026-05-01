from langchain.tools import BaseTool
import pandas as pd
from datetime import datetime, timedelta
import random

class MarketPriceTool(BaseTool):
    name: str = "Market Price Fetcher and Predictor"
    description: str = "Fetches current wholesale prices for a crop in nearby mandis and provides a 7-day predicted trend."
    
    def _run(self, crop: str, location_lat: float = None, location_lon: float = None, **kwargs) -> str:
        # Normalize crop name
        crop = str(crop).strip().lower()
        if not crop or crop == "none":
            return "Please specify a crop to get market prices."
            
        # MOCK IMPLEMENTATION OF DAM (Department of Agricultural Marketing) Data
        # In a production scenario with a stable API, we would use httpx here.
        # For now, we generate structured, realistic mock data for Bangladeshi Mandis.
        
        mandis = ["Karwan Bazar, Dhaka", "Shyam Bazar, Dhaka", "Rajshahi Sadar Mandi", "Khulna Boro Bazar", "Bogura Mohasthan Hat"]
        
        # Base prices per kg (in BDT) for common crops
        base_prices = {
            "potato": 45,
            "onion": 80,
            "rice": 65,
            "tomato": 120,
            "brinjal": 60,
            "cabbage": 35,
            "chili": 150
        }
        
        # Fallback to a random base price if crop is unknown
        base_price = base_prices.get(crop, random.randint(40, 150))
        
        # Generate current prices across mandis with slight regional variations
        current_prices = []
        for mandi in mandis:
            variation = random.uniform(0.85, 1.15)
            current_prices.append({
                "mandi": mandi,
                "price_bdt_per_kg": round(base_price * variation, 2),
                "distance_km": random.randint(5, 150) # Mock distance
            })
            
        # Sort by best price (highest)
        current_prices.sort(key=lambda x: x["price_bdt_per_kg"], reverse=True)
        
        # Generate 7-day Simple Moving Average Prediction (Trend)
        # We simulate 14 days of past data
        past_dates = [datetime.now() - timedelta(days=i) for i in range(14, 0, -1)]
        past_prices = [round(base_price * random.uniform(0.9, 1.1), 2) for _ in range(14)]
        
        df = pd.DataFrame({"date": past_dates, "price": past_prices})
        df["sma_7"] = df["price"].rolling(window=7).mean()
        
        # Simple heuristic: if the last price is below SMA, it might rebound (Uptrend).
        # If it's above SMA, it might correct (Downtrend).
        latest_price = df.iloc[-1]["price"]
        latest_sma = df.iloc[-1]["sma_7"]
        
        if latest_price < latest_sma * 0.95:
            trend = "Strong Uptrend Expected (Hold to sell later)"
            pred_7_day = round(latest_price * 1.10, 2)
        elif latest_price > latest_sma * 1.05:
            trend = "Downtrend Expected (Sell immediately)"
            pred_7_day = round(latest_price * 0.90, 2)
        else:
            trend = "Stable (Sell at your convenience)"
            pred_7_day = round(latest_price * 1.02, 2)
            
        # Format the output for the LLM
        output = f"--- MARKET INTELLIGENCE FOR {crop.upper()} ---\n"
        output += "CURRENT WHOLESALE PRICES (BDT/KG):\n"
        for p in current_prices[:3]: # Top 3 best markets
            output += f"- {p['mandi']}: {p['price_bdt_per_kg']} BDT (Distance: ~{p['distance_km']} km)\n"
            
        output += "\nPRICE PREDICTION & ARBITRAGE (Next 7 Days):\n"
        output += f"- Current Avg Price: {latest_price} BDT\n"
        output += f"- 7-Day SMA Baseline: {round(latest_sma, 2)} BDT\n"
        output += f"- Predicted Price (7 days): {pred_7_day} BDT\n"
        output += f"- Market Trend: {trend}\n\n"
        output += "Advice: Consider transport costs (avg 2-5 BDT/kg per 50km) before traveling to a distant mandi for a slightly higher price."
        
        return output
