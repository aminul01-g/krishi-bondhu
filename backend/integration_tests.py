import asyncio
import pytest
from app.crews.krishi_crew import KrishiCrewOrchestrator
from app.db import AsyncSessionLocal
from app.models.db_models import SoilTestLog, IrrigationLog

# Orchestrator instance
orchestrator = KrishiCrewOrchestrator()

@pytest.mark.asyncio
async def test_soil_analysis_flow():
    print("\n[Integration] Testing Soil Health Advisor...")
    initial_state = {
        "transcript": "Soil analysis request: please analyze this soil for Rice crop",
        "user_id": "test_user",
        "gps": {"lat": 23.81, "lon": 90.41}
    }
    # Manually trigger intent since router might be fuzzy
    result = await orchestrator.ainvoke(initial_state)
    print(f"Reply: {result.get('reply_text')}")
    assert len(result.get('reply_text')) > 0
    print("✓ Soil Analysis Flow Verified")

@pytest.mark.asyncio
async def test_irrigation_advice_flow():
    print("[Integration] Testing Irrigation Advisor...")
    initial_state = {
        "transcript": "water advice for rice crop at location 23.81, 90.41",
        "user_id": "test_user",
        "gps": {"lat": 23.81, "lon": 90.41}
    }
    result = await orchestrator.ainvoke(initial_state)
    print(f"Reply: {result.get('reply_text')}")
    assert len(result.get('reply_text')) > 0
    print("✓ Irrigation Advisor Flow Verified")

@pytest.mark.asyncio
async def test_finance_navigator_flow():
    print("[Integration] Testing Finance Navigator...")
    initial_state = {
        "transcript": "Finance request: Subsidies for Rice",
        "user_id": "test_user",
        "gps": {"lat": 23.81, "lon": 90.41}
    }
    # Pass inputs dict explicitly if needed by the orchestrator
    result = await orchestrator.ainvoke(initial_state)
    print(f"Reply: {result.get('reply_text')}")
    assert result.get('reply_text') is not None
    print("✓ Finance Navigator Flow Verified")

if __name__ == "__main__":
    # Manually running tests since integration suite requires orchestration
    asyncio.run(test_soil_analysis_flow())
    asyncio.run(test_irrigation_advice_flow())
    asyncio.run(test_finance_navigator_flow())
    print("\nAll Integration Tests Passed!")
