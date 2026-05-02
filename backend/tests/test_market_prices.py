"""
Unit tests for Market Price Intelligence feature
Tests market price fetching, persistence, and historical retrieval
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.db_models import Base, MarketPrice
from app.tools.market_tool import MarketPriceTool

# Create in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
async def test_db_session():
    """Create a test database session."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_market_price_tool_run(test_db_session):
    """Test the basic market price fetching functionality."""
    tool = MarketPriceTool()
    
    # Test with potato
    result = tool._run("potato")
    assert "MARKET INTELLIGENCE" in result
    assert "POTATO" in result
    assert "CURRENT WHOLESALE PRICES" in result
    assert "BDT" in result
    
    # Test with rice
    result = tool._run("rice")
    assert "RICE" in result

@pytest.mark.asyncio
async def test_market_price_persistence(test_db_session):
    """Test saving market prices to database."""
    tool = MarketPriceTool()
    
    # Generate market data
    tool._run("potato")
    
    # Save to database
    await tool.save_prices_to_db(test_db_session)
    
    # Verify data was saved
    from sqlalchemy import select
    stmt = select(MarketPrice).where(MarketPrice.crop == "potato")
    result = await test_db_session.execute(stmt)
    prices = result.scalars().all()
    
    assert len(prices) > 0
    assert prices[0].crop == "potato"
    assert prices[0].price_bdt_per_kg > 0

@pytest.mark.asyncio
async def test_market_price_history_retrieval(test_db_session):
    """Test retrieving historical price data."""
    tool = MarketPriceTool()
    
    # Create sample market price records
    for i in range(5):
        price = MarketPrice(
            crop="tomato",
            mandi=f"Mandi_{i}",
            price_bdt_per_kg=100 + i * 10,
            distance_km=50,
            prediction_7day=120,
            market_trend="Stable"
        )
        test_db_session.add(price)
    
    await test_db_session.commit()
    
    # Test retrieval
    history = await tool.get_price_history(test_db_session, "tomato", days=7)
    
    assert "crop" in history
    assert history["crop"] == "tomato"
    assert "mandi_averages" in history
    assert len(history["mandi_averages"]) > 0

@pytest.mark.asyncio
async def test_market_price_no_history():
    """Test behavior when no price history exists."""
    tool = MarketPriceTool()
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        history = await tool.get_price_history(session, "unknown_crop", days=7)
        assert "message" in history
        assert "No price history" in history["message"]

def test_market_price_trend_prediction():
    """Test price trend prediction logic."""
    tool = MarketPriceTool()
    
    # Test multiple crops to ensure variety
    crops = ["potato", "onion", "rice", "tomato", "brinjal"]
    
    for crop in crops:
        result = tool._run(crop)
        # Verify trend is one of the expected values
        assert any(trend in result for trend in ["Uptrend", "Downtrend", "Stable"])
        # Verify predicted price is included
        assert "Predicted Price" in result

def test_market_price_tool_invalid_crop():
    """Test handling of invalid/unknown crops."""
    tool = MarketPriceTool()
    
    # Empty string should return error message
    result = tool._run("")
    assert "Please specify a crop" in result
    
    # None should return error message
    result = tool._run("none")
    assert "Please specify a crop" in result

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
