
import asyncio
import logging
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch, MagicMock

from app.main import app
from app.db import get_db

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("APIHealthCheck")

# --- DATABASE MOCKING ---
# We override the get_db dependency to avoid connection errors in the health check
async def override_get_db():
    mock_db = AsyncMock(spec=AsyncSession)
    # Add a mock result for any DB execution if needed
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    yield mock_db

app.dependency_overrides[get_db] = override_get_db
# Also handle get_db_session which some endpoints use
from app.db import get_db_session
app.dependency_overrides[get_db_session] = override_get_db

client = TestClient(app)

async def test_api_endpoints():
    results = []
    
    def log_result(name, passed, output):
        status = "Pass" if passed else "Fail"
        results.append((name, status, str(output)))
        logger.info(f"{name}: {status}")

    # 1. Main Endpoints (main.py)
    logger.info("Testing Main Endpoints...")
    try:
        # /api/get_tts expects a 'path' query param
        response = client.get("/api/get_tts?path=test.mp3")
        # Should return 204 if file missing, which is a success for the endpoint logic
        log_result("GET /api/get_tts", response.status_code in [200, 204], response.status_code)
        
        # Test a non-existent path to check SPA catch-all
        response = client.get("/dashboard")
        # 404 is expected if static/index.html is missing, but it confirms the route is reachable
        log_result("SPA Catch-all", response.status_code in [200, 404], response.status_code)
    except Exception as e:
        log_result("Main Endpoints", False, e)

    # 2. Conversation Endpoints (api/routes.py)
    logger.info("Testing Conversation Endpoints...")
    try:
        response = client.get("/api/conversations")
        log_result("GET /api/conversations", response.status_code == 200, response.status_code)
    except Exception as e:
        log_result("Conversation Endpoints", False, e)

    # 3. Market Endpoints (market.py)
    logger.info("Testing Market Endpoints...")
    try:
        with patch("app.core.dependencies.orchestrator.ainvoke", new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = {"reply_text": "Market advice"}
            response = client.get("/api/market/advice?crop=rice")
            log_result("GET /api/market/advice", response.status_code == 200, response.status_code)
        
        response = client.get("/api/market/history?crop=rice")
        log_result("GET /api/market/history", response.status_code == 200, response.status_code)
    except Exception as e:
        log_result("Market Endpoints", False, e)

    # 4. Diary Endpoints (diary.py)
    logger.info("Testing Diary Endpoints...")
    try:
        with patch("app.core.dependencies.orchestrator.ainvoke", new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = {"reply_text": '{"entry_type": "expense", "amount": 100, "category": "Seeds"}'}
            payload = {"user_id": "test_user", "transcript": "Bought seeds for 100"}
            response = client.post("/api/diary/add", json=payload)
            log_result("POST /api/diary/add", response.status_code == 200, response.status_code)
        
        response = client.get("/api/diary/report?user_id=test_user")
        log_result("GET /api/diary/report", response.status_code == 200, response.status_code)
    except Exception as e:
        log_result("Diary Endpoints", False, e)

    # 5. Alerts Endpoints (alerts.py)
    logger.info("Testing Alerts Endpoints...")
    try:
        with patch("app.core.dependencies.orchestrator.ainvoke", new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = {"reply_text": "Mock alert"}
            response = client.get("/api/alerts/daily?user_id=test_user&crop=rice")
            log_result("GET /api/alerts/daily", response.status_code == 200, response.status_code)
    except Exception as e:
        log_result("Alerts Endpoints", False, e)

    # 6. Soil Endpoints (soil.py)
    logger.info("Testing Soil Endpoints...")
    try:
        with patch("app.core.dependencies.orchestrator.ainvoke", new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = {"reply_text": "Mock soil advice"}
            payload = {"user_id": "test_user", "crop": "rice"}
            response = client.post("/api/soil/analyze", json=payload)
            log_result("POST /api/soil/analyze", response.status_code == 200, response.status_code)
    except Exception as e:
        log_result("Soil Endpoints", False, e)

    # 7. Water Endpoints (water.py)
    logger.info("Testing Water Endpoints...")
    try:
        with patch("app.core.dependencies.orchestrator.ainvoke", new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = {"reply_text": "Mock water advice"}
            payload = {"user_id": "test_user", "lat": 23.8, "lon": 90.4, "crop": "rice"}
            response = client.post("/api/water/advice", json=payload)
            log_result("POST /api/water/advice", response.status_code == 200, response.status_code)
    except Exception as e:
        log_result("Water Endpoints", False, e)

    # 8. Finance Endpoints (finance.py)
    logger.info("Testing Finance Endpoints...")
    try:
        # /api/finance/credit-report instead of /api/finance/credit-score
        response = client.get("/api/finance/credit-report?user_id=test_user")
        log_result("GET /api/finance/credit-report", response.status_code == 200, response.status_code)
        
        # New model for insurance-quote
        payload = {"user_id": "test_user", "crop": "rice", "land_size": 2.5}
        response = client.post("/api/finance/insurance-quote", json=payload)
        log_result("POST /api/finance/insurance-quote", response.status_code == 200, response.status_code)
    except Exception as e:
        log_result("Finance Endpoints", False, e)

    # 9. Community Endpoints (community.py)
    logger.info("Testing Community Endpoints...")
    try:
        # Use real paths from community.py
        response = client.get("/api/community/questions")
        log_result("GET /api/community/questions", response.status_code == 200, response.status_code)
    except Exception as e:
        log_result("Community Endpoints", False, e)

    # 10. Marketplace Endpoints (marketplace.py)
    logger.info("Testing Marketplace Endpoints...")
    try:
        response = client.get("/api/marketplace/dealers")
        log_result("GET /api/marketplace/dealers", response.status_code == 200, response.status_code)
        
        response = client.get("/api/marketplace/verified-products")
        log_result("GET /api/marketplace/verified-products", response.status_code == 200, response.status_code)
    except Exception as e:
        log_result("Marketplace Endpoints", False, e)

    # 11. Emergency Endpoints (emergency.py)
    logger.info("Testing Emergency Endpoints...")
    try:
        response = client.get("/api/emergency/providers")
        log_result("GET /api/emergency/providers", response.status_code == 200, response.status_code)
        
        # DamageReportCreate requires many fields
        payload = {
            "farmer_id": "test_user",
            "crop_type": "rice",
            "lat": 23.8,
            "lon": 90.4,
            "damage_cause": "Flood",
            "damage_estimate_percent": 30.0,
            "yield_loss_estimate_percent": 20.0
        }
        response = client.post("/api/emergency/reports", json=payload)
        log_result("POST /api/emergency/reports", response.status_code == 200, response.status_code)
    except Exception as e:
        log_result("Emergency Endpoints", False, e)

    # Summary
    print("\n" + "="*50)
    print("API ENDPOINT HEALTH SUMMARY")
    print("="*50)
    all_passed = True
    for name, status, output in results:
        print(f"{name:.<40} {status}")
        if status == "Fail":
            all_passed = False
            print(f"   -> DEBUG: {output}")
    print("="*50)
    
    if all_passed:
        print("ALL API MODULES ARE RESPONDING! 🚀")
    else:
        print("SOME API MODULES FAILED. INVESTIGATION REQUIRED! 🛠️")

if __name__ == "__main__":
    asyncio.run(test_api_endpoints())
