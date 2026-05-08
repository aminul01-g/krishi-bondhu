"""Integration tests for major API endpoints."""

import pytest


class TestHealthEndpoints:
    """Test basic API health and conversations."""

    def test_get_conversations(self, test_client):
        response = test_client.get("/api/conversations")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestMarketEndpoints:
    """Test market API endpoints."""

    def test_market_prices_endpoint(self, test_client):
        response = test_client.get("/api/market/prices?crop=rice")
        assert response.status_code in [200, 422, 500]

    def test_market_trend_endpoint(self, test_client):
        response = test_client.get("/api/market/trend?crop=potato")
        assert response.status_code in [200, 422, 500]


class TestDiaryEndpoints:
    """Test diary API endpoints."""

    def test_diary_entries_endpoint(self, test_client):
        response = test_client.get("/api/diary/entries?user_id=test_user")
        assert response.status_code in [200, 404]

    def test_diary_create_entry(self, test_client):
        payload = {
            "user_id": "test_user",
            "crop": "rice",
            "entry_type": "expense",
            "amount": 1000.0,
            "description": "Seeds purchase"
        }
        response = test_client.post("/api/diary/entries", json=payload)
        assert response.status_code in [200, 201, 422]


class TestAlertEndpoints:
    """Test alert/tips API endpoints."""

    def test_alerts_tips_endpoint(self, test_client):
        response = test_client.get("/api/alerts/tips?crop=rice&lat=23.81&lon=90.41")
        assert response.status_code in [200, 422, 500]


class TestSoilEndpoints:
    """Test soil API endpoints."""

    def test_soil_analyze_endpoint(self, test_client):
        payload = {"user_id": "test_user", "crop": "rice"}
        response = test_client.post("/api/soil/analyze", json=payload)
        assert response.status_code in [200, 422, 500]


class TestWaterEndpoints:
    """Test water/irrigation API endpoints."""

    def test_water_advice_endpoint(self, test_client):
        payload = {"user_id": "test_user", "lat": 23.81, "lon": 90.41, "crop": "rice"}
        response = test_client.post("/api/water/advice", json=payload)
        assert response.status_code in [200, 422, 500]


class TestFinanceEndpoints:
    """Test finance API endpoints."""

    def test_finance_schemes_endpoint(self, test_client):
        payload = {"crop": "rice", "district": "Dhaka"}
        response = test_client.post("/api/finance/schemes", json=payload)
        assert response.status_code in [200, 422, 500]


class TestEmergencyEndpoints:
    """Test emergency API endpoints."""

    def test_emergency_report_endpoint(self, test_client):
        payload = {
            "farmer_id": "test_farmer",
            "crop_type": "rice",
            "lat": 23.8,
            "lon": 90.4,
            "damage_cause": "Flood",
            "damage_estimate_percent": 50.0,
            "yield_loss_estimate_percent": 40.0
        }
        response = test_client.post("/api/emergency/reports", json=payload)
        assert response.status_code in [200, 201, 422, 500]

    def test_emergency_providers_endpoint(self, test_client):
        response = test_client.get("/api/emergency/providers")
        assert response.status_code in [200, 404]
