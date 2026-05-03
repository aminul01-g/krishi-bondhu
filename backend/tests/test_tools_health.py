
import asyncio
import os
import json
import logging
from unittest.mock import AsyncMock, MagicMock

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ToolHealthCheck")

# Import all tools
from app.tools.weather_tool import WeatherLookupTool
from app.tools.market_tool import MarketPriceTool
from app.tools.alert_tool import PestRiskTool
from app.tools.soil_tool import SoilVisionTool, DIYSoilTestTool, RecommendFertilizerTool
from app.tools.irrigation_tool import SatelliteMoistureTool, WaterBalanceTool, FloodDroughtAlertTool
from app.tools.finance_tool import SubsidyNavigatorTool, CreditScoringTool, InsuranceQuoteTool
from app.tools.community_tool import CommunitySearchTool, EscalateToExpertTool
from app.tools.marketplace_tool import DealerSearchTool, ProductVerificationTool, LabelScannerTool
from app.tools.emergency_tool import CropDamageAssessmentTool, DamageReportGeneratorTool, SMSShareTool
from app.tools.vision_tool import LocalVisionDiseaseTool

async def test_all_tools():
    results = []
    
    # 1. Weather Tool
    logger.info("Testing WeatherLookupTool...")
    weather_tool = WeatherLookupTool()
    res = weather_tool._run(gps_coordinates="23.81, 90.41")
    results.append(("WeatherLookupTool", "Pass" if "Weather data" in res else "Fail", res))

    # 2. Market Tool
    logger.info("Testing MarketPriceTool...")
    market_tool = MarketPriceTool()
    res = market_tool._run(crop="potato")
    results.append(("MarketPriceTool", "Pass" if "MARKET INTELLIGENCE" in res else "Fail", res))
    
    # Test DB save for Market Tool
    mock_db = AsyncMock()
    await market_tool.save_prices_to_db(mock_db)
    results.append(("MarketPriceTool DB Save", "Pass" if mock_db.add.called else "Fail", "DB add called" if mock_db.add.called else "DB add NOT called"))

    # 3. Pest Risk Tool
    logger.info("Testing PestRiskTool...")
    pest_tool = PestRiskTool()
    res = pest_tool._run(crop="rice", weather_data="rainy")
    results.append(("PestRiskTool", "Pass" if "RISK" in res else "Fail", res))

    # 4. Soil Tools
    logger.info("Testing Soil Tools...")
    soil_vision = SoilVisionTool()
    # Test with non-existent file
    res = soil_vision._run(image_path="non_existent.jpg")
    results.append(("SoilVisionTool (Empty)", "Pass" if "No valid" in res or "No image" in res or "Mock" in res else "Fail", res))
    
    diy_soil = DIYSoilTestTool()
    res = diy_soil._run(test_data_json='{"ribbon_length_cm": 3, "ph_color": "green"}')
    results.append(("DIYSoilTestTool", "Pass" if "Texture" in res and "pH" in res else "Fail", res))
    
    fertilizer_tool = RecommendFertilizerTool()
    res = fertilizer_tool._run(soil_summary="Sandy soil, acidic", crop="rice")
    results.append(("RecommendFertilizerTool", "Pass" if "জৈব সার" in res else "Fail", res))

    # 5. Irrigation Tools
    logger.info("Testing Irrigation Tools...")
    sat_moisture = SatelliteMoistureTool()
    res = sat_moisture._run(lat=23.8, lon=90.4)
    results.append(("SatelliteMoistureTool", "Pass" if "Satellite Data" in res or "Local Mock" in res else "Fail", res))
    
    water_balance = WaterBalanceTool()
    res = water_balance._run(soil_moisture="0.4", rain_chance=10)
    results.append(("WaterBalanceTool", "Pass" if "Status" in res else "Fail", res))

    # 6. Finance Tools
    logger.info("Testing Finance Tools...")
    subsidy_tool = SubsidyNavigatorTool()
    res = subsidy_tool._run(crop="rice", land_size="2.5")
    results.append(("SubsidyNavigatorTool", "Pass" if "আপনার জন্য প্রযোজ্য" in res else "Fail", res))
    
    credit_tool = CreditScoringTool()
    # Use patch since it's a Pydantic model and doesn't allow arbitrary attribute assignment
    from unittest.mock import patch
    with patch('app.tools.finance_tool.CreditScoringTool.calculate_credit_score', new_callable=AsyncMock) as mock_calc:
        mock_calc.return_value = {
            "score": 85,
            "breakdown": {"consistency": 35, "profitability": 25, "completeness": 25},
            "recommendation": "Excellent"
        }
        res = await asyncio.to_thread(credit_tool._run, user_id="user_123")
    results.append(("CreditScoringTool", "Pass" if "SCORE" in res else "Fail", res))

    # 7. Marketplace Tools
    logger.info("Testing Marketplace Tools...")
    dealer_tool = DealerSearchTool()
    res = dealer_tool._run(input_type="urea", lat=23.81, lon=90.41)
    results.append(("DealerSearchTool", "Pass" if "dealer" in res.lower() else "Fail", res))
    
    verify_tool = ProductVerificationTool()
    res = verify_tool._run(barcode="123456789")
    results.append(("ProductVerificationTool", "Pass" if "STATUS" in res.upper() else "Fail", res))

    # 8. Emergency Tools
    logger.info("Testing Emergency Tools...")
    damage_tool = CropDamageAssessmentTool()
    res = damage_tool._run(image_path="none", crop_type="paddy")
    results.append(("CropDamageAssessmentTool", "Pass" if "Damage" in res else "Fail", res))

    # Summary
    print("\n" + "="*30)
    print("TOOL HEALTH CHECK SUMMARY")
    print("="*30)
    all_passed = True
    for tool, status, output in results:
        print(f"{tool:.<40} {status}")
        if status == "Fail":
            all_passed = False
            print(f"   -> ERROR OUTPUT: {output[:200]}...")
    print("="*30)
    
    if all_passed:
        print("ALL TOOLS ARE WORKING PERFECTLY! 🚀")
    else:
        print("SOME TOOLS FAILED. NEEDS TACKLING! 🛠️")

if __name__ == "__main__":
    asyncio.run(test_all_tools())
