"""Tests for Market Service and tools."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


class TestMarketServiceNormalize:
    """Test MarketService.normalize_crop()."""

    def test_normalize_basic(self):
        from app.services.market_service import MarketService
        assert MarketService.normalize_crop("Rice") == "rice"
        assert MarketService.normalize_crop("  POTATO  ") == "potato"

    def test_normalize_empty(self):
        from app.services.market_service import MarketService
        assert MarketService.normalize_crop("") == ""
        assert MarketService.normalize_crop(None) == ""


class TestMarketServicePrices:
    """Test get_current_prices structure."""

    @pytest.mark.asyncio
    async def test_get_current_prices_returns_valid_structure(self):
        with patch("app.services.market_service.Redis") as mock_redis_cls:
            mock_redis = MagicMock()
            mock_redis.get.return_value = None
            mock_redis.setex.return_value = True
            mock_redis_cls.from_url.return_value = mock_redis

            from app.services.market_service import MarketService
            svc = MarketService()
            svc.redis = mock_redis

            result = await svc.get_current_prices("rice")

            assert "crop" in result
            assert "current_prices" in result
            assert isinstance(result["current_prices"], list)
            assert len(result["current_prices"]) > 0
            assert "price_bdt_per_kg" in result["current_prices"][0]

    @pytest.mark.asyncio
    async def test_get_current_prices_invalid_crop(self):
        with patch("app.services.market_service.Redis") as mock_redis_cls:
            mock_redis = MagicMock()
            mock_redis.get.return_value = None
            mock_redis_cls.from_url.return_value = mock_redis

            from app.services.market_service import MarketService
            svc = MarketService()
            svc.redis = mock_redis

            result = await svc.get_current_prices("")
            assert "error" in result


class TestMarketServiceTrendFallback:
    """Test predict_price_trend fallback when no model file exists."""

    @pytest.mark.asyncio
    async def test_trend_fallback_no_model(self, db_session):
        with patch("app.services.market_service.Redis") as mock_redis_cls:
            mock_redis = MagicMock()
            mock_redis.get.return_value = None
            mock_redis_cls.from_url.return_value = mock_redis

            from app.services.market_service import MarketService
            svc = MarketService()
            svc.redis = mock_redis
            svc.models_dir = "/nonexistent"

            result = await svc.predict_price_trend("rice", db_session)

            assert result["confidence"] == "Low (Heuristic Fallback)"
            assert result["trend"] == "Stable (Baseline)"


class TestMarketServiceCache:
    """Test Redis cache hit behavior."""

    @pytest.mark.asyncio
    async def test_cache_hit(self):
        import json
        cached_data = json.dumps({
            "crop": "rice",
            "current_prices": [{"mandi": "Test", "price_bdt_per_kg": 70.0}],
            "timestamp": "2026-01-01T00:00:00"
        })

        with patch("app.services.market_service.Redis") as mock_redis_cls:
            mock_redis = MagicMock()
            mock_redis.get.return_value = cached_data
            mock_redis_cls.from_url.return_value = mock_redis

            from app.services.market_service import MarketService
            svc = MarketService()
            svc.redis = mock_redis

            result = await svc.get_current_prices("rice")
            assert result["crop"] == "rice"
            mock_redis.setex.assert_not_called()
