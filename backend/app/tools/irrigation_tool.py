from langchain.tools import BaseTool
import httpx
import pandas as pd
from datetime import datetime, timedelta
import logging
import os

logger = logging.getLogger("IrrigationTools")

class SatelliteMoistureTool(BaseTool):
    name: str = "Satellite Soil Moisture Fetcher"
    description: str = "Fetches root-zone soil wetness index (0-1) from satellite data for a given GPS location."
    
    def _run(self, lat: float = None, lon: float = None, gps: str = None, **kwargs) -> str:
        # If gps string is provided instead of lat/lon
        if gps and (not lat or not lon):
            try:
                import re
                nums = re.findall(r"[-+]?\d*\.\d+|\d+", str(gps))
                if len(nums) >= 2:
                    lat, lon = float(nums[0]), float(nums[1])
            except Exception:
                pass

        if not lat or not lon:
            return "GPS coordinates missing or invalid. Cannot fetch satellite moisture."
            
        # NASA POWER API for Root Zone Soil Wetness (GWETROOT)
        # We fetch for the last 3 days to get a stable average
        today = datetime.now()
        start_date = (today - timedelta(days=3)).strftime("%Y%m%d")
        end_date = today.strftime("%Y%m%d")
        
        url = (
            f"https://power.larc.nasa.gov/api/temporal/daily/point?"
            f"parameters=GWETROOT&community=AG&longitude={lon}&latitude={lat}&"
            f"start={start_date}&end={end_date}&format=JSON"
        )
        
        try:
            # Setting a short timeout to prevent blocking the agent
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    moisture_data = data['properties']['parameter']['GWETROOT']
                    # Filter out -999 fill values
                    values = [v for v in moisture_data.values() if v != -999]
                    if values:
                        avg_moisture = sum(values) / len(values)
                        return f"Satellite Data: Average Root Zone Soil Wetness is {avg_moisture:.2f} (Index 0-1)."
                    else:
                        return "Satellite Data: Moisture data currently unavailable for this location (Fill values detected)."
                else:
                    return f"Satellite Data: API returned error code {response.status_code}."
        except Exception as e:
            logger.warning(f"NASA POWER API call failed: {e}. Falling back to mock.")
            
        # Mock Fallback
        return "Local Mock: Current Root Zone Soil Wetness is 0.35 (Index 0-1). Conditions are slightly dry."

class WaterBalanceTool(BaseTool):
    name: str = "Irrigation Advice Engine"
    description: str = "Calculates irrigation advice based on soil moisture and weather forecast."
    
    def _run(self, soil_moisture: str, rain_chance: float = 0.0, expected_precip_mm: float = 0.0) -> str:
        # Extract moisture value from string (e.g., "0.35")
        import re
        moisture_match = re.search(r"(\d+\.\d+)", str(soil_moisture))
        moisture = float(moisture_match.group(1)) if moisture_match else 0.5
        
        advice = []
        status = "Normal"
        
        # 1. Irrigation Decision
        if moisture < 0.4:
            if rain_chance < 40 and expected_precip_mm < 5.0:
                advice.append("মাটিতে পানির অভাব দেখা দিয়েছে। আগামী ২৪ ঘণ্টার মধ্যে ১৫-২০ মি.মি. সেচ প্রয়োগ করুন।")
                status = "Needs Irrigation"
            else:
                advice.append(f"মাটি শুকনো হলেও আগামী ২৪ ঘণ্টায় বৃষ্টির সম্ভাবনা ({rain_chance}%) আছে। সেচ দেওয়ার আগে বৃষ্টির জন্য অপেক্ষা করুন।")
                status = "Wait for Rain"
        elif moisture > 0.8:
            advice.append("মাটিতে অতিরিক্ত আর্দ্রতা আছে। আপাতত সেচের প্রয়োজন নেই, বরং পানি নিষ্কাশনের ব্যবস্থা রাখুন।")
            status = "Saturated"
        else:
            advice.append("মাটির আর্দ্রতা বর্তমানে সন্তোষজনক। আগামী ২-৩ দিন সেচের প্রয়োজন নেই।")
            status = "Adequate"
            
        return f"Status: {status}\nAdvice: {advice[0]}"

class FloodDroughtAlertTool(BaseTool):
    name: str = "Water Hazard Alert Tool"
    description: str = "Provides alerts for impending flood or drought risks based on forecast data."
    
    def _run(self, precip_7_day_mm: float, regional_elevation_m: float = 10.0) -> str:
        # In a real scenario, this would check FFWC (Flood Forecasting and Warning Centre) data
        total_precip = float(precip_7_day_mm)
        
        if total_precip > 200:
            return "সতর্কতা (রেড এলার্ট): আগামী ৭ দিনে ভারী বৃষ্টিপাতের (২০০ মি.মি.+) সম্ভাবনা আছে। বন্যার ঝুঁকি বেশি। নিচু জমি থেকে ফসল দ্রুত সংগ্রহ করুন।"
        elif total_precip > 100:
            return "সতর্কতা (হলুদ এলার্ট): মাঝারি থেকে ভারী বৃষ্টির সম্ভাবনা। জলাবদ্ধতা এড়াতে নালা পরিষ্কার রাখুন।"
        elif total_precip < 5 and total_precip >= 0:
            return "সতর্কতা: দীর্ঘ সময় বৃষ্টি না হওয়ায় খরা পরিস্থিতি তৈরি হতে পারে। সেচ ব্যবস্থা সচল রাখুন।"
        
        return "বর্তমানে বড় কোনো পানিসম্পদ সংক্রান্ত ঝুঁকি নেই।"
