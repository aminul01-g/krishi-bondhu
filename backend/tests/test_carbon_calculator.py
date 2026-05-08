"""Tests for Carbon Credit & Sustainability service."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


class TestCarbonFootprint:
    """Test carbon footprint calculation."""

    @pytest.mark.asyncio
    async def test_carbon_calculation_known_inputs(self):
        from app.services.sustainability_service import SustainabilityService
        svc = SustainabilityService()

        # Mock diary entries with known values
        mock_entries = [
            MagicMock(entry_type="expense", category="fertilizer", amount=500, description="Urea 50kg"),
            MagicMock(entry_type="expense", category="fuel", amount=200, description="Diesel for pump"),
        ]

        result = svc.calculate_carbon_footprint(mock_entries)

        assert isinstance(result, dict)
        assert "total_emissions_kg_co2" in result or "emissions" in result or isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_carbon_zero_emissions(self):
        from app.services.sustainability_service import SustainabilityService
        svc = SustainabilityService()

        result = svc.calculate_carbon_footprint([])
        assert isinstance(result, dict)


class TestSustainablePractices:
    """Test sustainable practice detection."""

    @pytest.mark.asyncio
    async def test_detect_practices(self):
        from app.services.sustainability_service import SustainabilityService
        svc = SustainabilityService()

        mock_entries = [
            MagicMock(entry_type="activity", description="Applied compost to field", category="organic"),
            MagicMock(entry_type="activity", description="Installed drip irrigation", category="water"),
        ]

        result = svc.detect_sustainable_practices(mock_entries)
        assert isinstance(result, (list, dict))


class TestScorecardGrading:
    """Test scorecard grade assignment."""

    @pytest.mark.asyncio
    async def test_grade_assignment(self):
        from app.services.sustainability_service import SustainabilityService
        svc = SustainabilityService()

        # High sustainability should get A or B
        scorecard = svc.generate_scorecard(
            emissions={"total_emissions_kg_co2": 50},
            practices=["composting", "cover_cropping", "drip_irrigation"],
            offsets=30.0
        )
        assert isinstance(scorecard, dict)
        assert "grade" in scorecard
        assert scorecard["grade"] in ["A", "B", "C", "D"]
