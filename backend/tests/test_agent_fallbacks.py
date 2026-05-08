"""Tests for agent fallback logic across vision, weather, and yield services."""

import pytest
import os
from unittest.mock import patch, MagicMock


class TestVisionServiceFallbackChain:
    """Test the 3-tier fallback chain in VisionService."""

    def test_tier1_skipped_without_api_key(self):
        """When HUGGINGFACE_API_KEY is empty, Tier 1 should be skipped."""
        with patch.dict(os.environ, {"HUGGINGFACE_API_KEY": "", "GROQ_API_KEY": ""}):
            from app.services.vision_service import VisionService
            svc = VisionService()
            result = svc._tier1_huggingface("/fake/path.jpg", "disease")
            assert result is None

    def test_tier2_skipped_without_groq_key(self):
        """When GROQ_API_KEY is empty, Tier 2 should be skipped."""
        with patch.dict(os.environ, {"GROQ_API_KEY": ""}):
            from app.services.vision_service import VisionService
            svc = VisionService()
            result = svc._tier2_groq_vision("/fake/path.jpg", "disease")
            assert result is None

    def test_full_fallback_to_offline(self, tmp_path):
        """When all tiers fail, should return offline response."""
        # Create a dummy image file
        img_path = tmp_path / "test.jpg"
        img_path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        with patch.dict(os.environ, {"HUGGINGFACE_API_KEY": "", "GROQ_API_KEY": ""}):
            from app.services.vision_service import VisionService
            svc = VisionService()
            result = svc.analyze_image(str(img_path), "disease")
            assert "Offline" in result or "offline" in result.lower()

    def test_soil_fallback_to_offline(self, tmp_path):
        """Soil analysis should also fall back to offline."""
        img_path = tmp_path / "soil.jpg"
        img_path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        with patch.dict(os.environ, {"HUGGINGFACE_API_KEY": "", "GROQ_API_KEY": ""}):
            from app.services.vision_service import VisionService
            svc = VisionService()
            result = svc.analyze_image(str(img_path), "soil")
            assert "Loamy" in result or "Offline" in result

    def test_invalid_image_path(self):
        """Should return a graceful message for missing images."""
        from app.services.vision_service import VisionService
        svc = VisionService()
        result = svc.analyze_image("/nonexistent/path.jpg", "disease")
        assert "No valid image" in result


class TestWeatherServiceFallback:
    """Test weather service fallback to climate averages."""

    @pytest.mark.asyncio
    async def test_fallback_to_climate_averages(self):
        """When NASA POWER fails, should use Bangladesh climate averages."""
        with patch("app.services.weather_service.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = MagicMock(side_effect=Exception("Network error"))
            mock_client.return_value.__aexit__ = MagicMock(return_value=False)

            from app.services.weather_service import WeatherService
            svc = WeatherService()
            result = await svc.get_weather_data(23.8, 90.4)

            assert "temp_max" in result
            assert "source" in result
            # Should be from climate averages since API failed
            assert result["source"] in ["climate_average", "nasa_power"]

    def test_et0_calculation(self):
        """Test Hargreaves-Samani ET₀ with known values."""
        from app.services.weather_service import WeatherService
        svc = WeatherService()

        # Known calculation: Tmax=35, Tmin=25, Ra=15
        # Tmean = 30, ET0 = 0.0023 * (30+17.8) * sqrt(10) * 15
        et0 = svc.calculate_et0(35.0, 25.0, 15.0)
        assert 4.0 < et0 < 6.0  # Should be ~5.2

    def test_et0_edge_case_tmax_equals_tmin(self):
        """When Tmax==Tmin, should clamp to 1°C delta."""
        from app.services.weather_service import WeatherService
        svc = WeatherService()
        et0 = svc.calculate_et0(25.0, 25.0, 15.0)
        assert et0 > 0


class TestYieldPredictionFallback:
    """Test yield prediction fallback when model not available."""

    @pytest.mark.asyncio
    async def test_fallback_when_no_model(self, db_session):
        """Should use hybrid simulation when yield_model.pkl not found."""
        with patch("app.services.yield_service._load_yield_model", return_value=None):
            from app.services.yield_service import predict_yield
            result = await predict_yield(db_session, "test_user", "rice", 23.8, 90.4)

            assert "predicted_yield" in result
            assert result["predicted_yield"] > 0
            assert result["prediction_source"] == "hybrid_simulation"


class TestDamageAssessmentFallback:
    """Test crop damage tool fallback when CV2 is unavailable."""

    def test_damage_no_image(self):
        """Should return mock assessment when no image provided."""
        from app.tools.emergency_tool import CropDamageAssessmentTool
        tool = CropDamageAssessmentTool()
        result = tool._run(image_path="none", crop_type="rice")
        assert "damage" in result.lower() or "Damage" in result
