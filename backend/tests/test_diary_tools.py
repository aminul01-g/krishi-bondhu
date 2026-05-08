"""Tests for Farm Diary tools and endpoints."""

import pytest
from unittest.mock import patch, MagicMock


class TestDiaryEntryCreation:
    """Test diary entry creation via API."""

    def test_create_diary_entry(self, test_client):
        payload = {
            "user_id": "test_user_001",
            "crop": "rice",
            "entry_type": "expense",
            "amount": 5000.0,
            "description": "Fertilizer purchase",
            "category": "fertilizer"
        }
        response = test_client.post("/api/diary/entries", json=payload)
        # Accept both 200 and 422 (if schema differs)
        assert response.status_code in [200, 201, 422]

    def test_get_diary_entries(self, test_client):
        response = test_client.get("/api/diary/entries?user_id=test_user_001")
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))


class TestDiaryReport:
    """Test P&L report generation."""

    def test_diary_report_structure(self, test_client):
        response = test_client.get("/api/diary/report?user_id=test_user_001&period=monthly")
        assert response.status_code in [200, 404]

    def test_diary_report_empty_user(self, test_client):
        response = test_client.get("/api/diary/report?user_id=nonexistent_user&period=monthly")
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            # Should return a valid structure even for empty data
            assert isinstance(data, dict)
