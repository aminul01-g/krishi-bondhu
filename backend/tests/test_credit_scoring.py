"""
Unit tests for Credit Readiness Scoring feature
Tests credit score calculation based on farm diary data
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.db_models import Base, FarmDiary
from app.tools.finance_tool import CreditScoringTool

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
async def test_credit_score_no_diary_entries(test_db_session):
    """Test credit scoring when no diary entries exist."""
    tool = CreditScoringTool()
    
    result = await tool.calculate_credit_score(test_db_session, "user_123")
    
    assert result["score"] == 0
    assert "কোনো ডায়েরি এন্ট্রি পাওয়া যায়নি" in result["message"]

@pytest.mark.asyncio
async def test_credit_score_with_good_entries(test_db_session):
    """Test credit scoring with good diary entries."""
    tool = CreditScoringTool()
    
    # Create good diary entries (weekly, profitable, complete)
    now = datetime.now()
    for week in range(0, 4):
        date = now - timedelta(days=week*7)
        
        # Income entry
        income = FarmDiary(
            user_id="user_456",
            date=date,
            entry_type="income",
            category="sales",
            amount=5000,
            unit="BDT",
            notes="Rice harvest sale - good quality",
            crop="rice",
            plot="Plot A"
        )
        test_db_session.add(income)
        
        # Expense entry
        expense = FarmDiary(
            user_id="user_456",
            date=date + timedelta(days=1),
            entry_type="expense",
            category="fertilizer",
            amount=2000,
            unit="BDT",
            notes="Urea fertilizer for winter crop",
            crop="rice",
            plot="Plot A"
        )
        test_db_session.add(expense)
    
    await test_db_session.commit()
    
    result = await tool.calculate_credit_score(test_db_session, "user_456")
    
    assert result["score"] > 50  # Should be decent score
    assert "consistency" in result["breakdown"]
    assert "profitability" in result["breakdown"]
    assert "completeness" in result["breakdown"]
    assert result["metrics"]["total_income"] > 0
    assert result["metrics"]["total_expense"] > 0
    assert "চমৎকার" in result["recommendation"] or "ভালো" in result["recommendation"]

@pytest.mark.asyncio
async def test_credit_score_with_poor_entries(test_db_session):
    """Test credit scoring with poor entries (incomplete, inconsistent)."""
    tool = CreditScoringTool()
    
    # Create single incomplete entry
    entry = FarmDiary(
        user_id="user_789",
        date=datetime.now(),
        entry_type="expense",
        category="labor",
        amount=1000,
        unit="BDT",
        notes=None,  # No notes
        crop=None,  # No crop
        plot=None   # No plot
    )
    test_db_session.add(entry)
    await test_db_session.commit()
    
    result = await tool.calculate_credit_score(test_db_session, "user_789")
    
    assert result["score"] < 50  # Should be low score
    assert result["breakdown"]["completeness"] == 0  # No complete entries
    assert "দুর্বল" in result["recommendation"] or "কম" in result["recommendation"]

@pytest.mark.asyncio
async def test_credit_score_profitability_calculation(test_db_session):
    """Test profitability scoring with different profit ratios."""
    tool = CreditScoringTool()
    
    # Create very profitable scenario (2x profit)
    date = datetime.now() - timedelta(days=3)
    
    income = FarmDiary(
        user_id="user_profit",
        date=date,
        entry_type="income",
        category="sales",
        amount=10000,
        unit="BDT",
        notes="Good harvest",
        crop="rice",
        plot="A"
    )
    expense = FarmDiary(
        user_id="user_profit",
        date=date,
        entry_type="expense",
        category="labor",
        amount=5000,
        unit="BDT",
        notes="Labor cost",
        crop="rice",
        plot="A"
    )
    test_db_session.add(income)
    test_db_session.add(expense)
    await test_db_session.commit()
    
    result = await tool.calculate_credit_score(test_db_session, "user_profit")
    
    # Profit ratio is 2.0 (10000/5000), should get full profitability score
    assert result["breakdown"]["profitability"] == 30
    assert result["metrics"]["net_profit"] == 5000

@pytest.mark.asyncio
async def test_credit_score_consistency_scoring(test_db_session):
    """Test consistency scoring based on weekly logging frequency."""
    tool = CreditScoringTool()
    
    # Create entries over 2 weeks (4 entries = 2 per week)
    dates = [datetime.now() - timedelta(days=i*2) for i in range(4)]
    
    for date in dates:
        entry = FarmDiary(
            user_id="user_consistent",
            date=date,
            entry_type="expense",
            category="seeds",
            amount=1000,
            unit="BDT",
            notes="Regular seed purchase",
            crop="vegetable",
            plot="B"
        )
        test_db_session.add(entry)
    
    await test_db_session.commit()
    
    result = await tool.calculate_credit_score(test_db_session, "user_consistent")
    
    # Should have decent consistency score
    assert result["breakdown"]["consistency"] > 0
    assert result["metrics"]["avg_entries_per_week"] > 1

def test_credit_scoring_tool_sync_wrapper():
    """Test the synchronous wrapper of credit scoring tool."""
    tool = CreditScoringTool()
    
    # Sync method should return a string message
    result = tool._run("user_123")
    assert "Credit scoring initiated" in result
    assert "user_123" in result

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
