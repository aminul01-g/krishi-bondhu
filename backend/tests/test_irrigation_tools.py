import os
import json
import asyncio
import httpx
from app.tools.irrigation_tool import SatelliteMoistureTool, WaterBalanceTool, FloodDroughtAlertTool

def test_satellite_moisture_tool():
    print("Testing SatelliteMoistureTool...")
    tool = SatelliteMoistureTool()
    # Test with valid GPS (Dhaka)
    # This will attempt a real API call if internet is available, or fallback to mock
    result = tool._run(lat=23.8103, lon=90.4125)
    print(f"Result: {result}")
    assert "Soil Wetness" in result or "Mock" in result

def test_water_balance_tool():
    print("\nTesting WaterBalanceTool...")
    tool = WaterBalanceTool()
    
    # Test Dry Condition (Needs Irrigation)
    result = tool._run(soil_moisture_str="0.30", rain_chance=20, expected_precip_mm=2.0)
    print(f"Result (Dry): {result}")
    assert "Needs Irrigation" in result
    assert "সেচ প্রয়োগ করুন" in result
    
    # Test Dry but Rain expected (Wait for Rain)
    result = tool._run(soil_moisture_str="0.30", rain_chance=80, expected_precip_mm=15.0)
    print(f"Result (Dry but Rain): {result}")
    assert "Wait for Rain" in result
    assert "বৃষ্টির জন্য অপেক্ষা করুন" in result

    # Test Saturated Condition
    result = tool._run(soil_moisture_str="0.85")
    print(f"Result (Saturated): {result}")
    assert "Saturated" in result
    assert "অতিরিক্ত আর্দ্রতা" in result

def test_flood_drought_alert_tool():
    print("\nTesting FloodDroughtAlertTool...")
    tool = FloodDroughtAlertTool()
    
    # Test Flood Risk
    result = tool._run(precip_7_day_mm=250.0)
    print(f"Result (Flood): {result}")
    assert "রেড এলার্ট" in result
    
    # Test Normal
    result = tool._run(precip_7_day_mm=50.0)
    print(f"Result (Normal): {result}")
    assert "ঝুঁকি নেই" in result

if __name__ == "__main__":
    test_satellite_moisture_tool()
    test_water_balance_tool()
    test_flood_drought_alert_tool()
    print("\nAll Irrigation Tools tests passed!")
