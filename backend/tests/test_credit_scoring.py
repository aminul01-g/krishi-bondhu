"""
Unit tests for the Credit Readiness Scoring feature.

Tests the production ``FinanceService.calculate_credit_score`` logic (score from
farm-diary data). Previously these tests targeted ``app.tools.finance_tool``
(an unused duplicate of the service) *and* declared their own async DB fixture,
which triggered a pytest-asyncio deprecation error. They now exercise the real
service path and use the shared ``db_session`` fixture from ``conftest.py``.
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, func
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.services.finance_service import FinanceService

# Isolated metadata containing ONLY the farm_diary table. The shared
# conftest fixture calls create_all() on the full Base, which includes
# PostGIS geometry columns (community_questions.location_geom) that cannot be
# created on SQLite. Credit scoring only reads farm_diary, so we mirror that
# one table here for a portable, self-contained in-memory test DB.
_DiaryBase = declarative_base()


class FarmDiary(_DiaryBase):
    __tablename__ = "farm_diary"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    date = Column(DateTime(timezone=True), server_default=func.now())
    entry_type = Column(String, nullable=False)
    category = Column(String, nullable=True)
    amount = Column(Float, nullable=False)
    unit = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    crop = Column(String, nullable=True)
    plot = Column(String, nullable=True)


@pytest_asyncio.fixture
async def db_session():
    """In-memory SQLite session with only the farm_diary table."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(_DiaryBase.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_credit_score_no_diary_entries(db_session):
    """Test credit scoring when no diary entries exist."""
    svc = FinanceService()
    result = await svc.calculate_credit_score(db_session, "user_123")

    assert result["score"] == 0
    assert result["breakdown"] == {"consistency": 0, "profitability": 0, "completeness": 0}
    # The no-data path returns a Bengali guidance recommendation.
    assert "recommendation" in result


@pytest.mark.asyncio
async def test_credit_score_with_good_entries(db_session):
    """Test credit scoring with good diary entries (weekly, profitable, complete)."""
    svc = FinanceService()

    now = datetime.now()
    for week in range(0, 4):
        date = now - timedelta(days=week * 7)
        db_session.add(
            FarmDiary(
                user_id="user_456", date=date, entry_type="income", category="sales",
                amount=5000, unit="BDT", notes="Rice harvest sale - good quality",
                crop="rice", plot="Plot A",
            )
        )
        db_session.add(
            FarmDiary(
                user_id="user_456", date=date + timedelta(days=1), entry_type="expense",
                category="fertilizer", amount=2000, unit="BDT",
                notes="Urea fertilizer for winter crop", crop="rice", plot="Plot A",
            )
        )
    await db_session.commit()

    result = await svc.calculate_credit_score(db_session, "user_456")

    assert result["score"] > 50  # profitable + complete + consistent
    assert "consistency" in result["breakdown"]
    assert "profitability" in result["breakdown"]
    assert "completeness" in result["breakdown"]
    # Income > expense (2.5x) → full profitability points.
    assert result["breakdown"]["profitability"] == 30


@pytest.mark.asyncio
async def test_credit_score_with_poor_entries(db_session):
    """Test credit scoring with a single incomplete entry."""
    svc = FinanceService()

    db_session.add(
        FarmDiary(
            user_id="user_789", date=datetime.now(), entry_type="expense",
            category="labor", amount=1000, unit="BDT",
            notes=None, crop=None, plot=None,  # incomplete → 0 completeness
        )
    )
    await db_session.commit()

    result = await svc.calculate_credit_score(db_session, "user_789")

    assert result["score"] < 50
    assert result["breakdown"]["completeness"] == 0


@pytest.mark.asyncio
async def test_credit_score_profitability_full_points(db_session):
    """Profit ratio >= 1.2 should yield full (30) profitability points."""
    svc = FinanceService()
    date = datetime.now() - timedelta(days=3)

    db_session.add(
        FarmDiary(
            user_id="user_profit", date=date, entry_type="income", category="sales",
            amount=10000, unit="BDT", notes="Good harvest", crop="rice", plot="A",
        )
    )
    db_session.add(
        FarmDiary(
            user_id="user_profit", date=date, entry_type="expense", category="labor",
            amount=5000, unit="BDT", notes="Labor cost", crop="rice", plot="A",
        )
    )
    await db_session.commit()

    result = await svc.calculate_credit_score(db_session, "user_profit")

    # Profit ratio is 2.0 (10000/5000) → full profitability score.
    assert result["breakdown"]["profitability"] == 30


@pytest.mark.asyncio
async def test_credit_score_consistency_scoring(db_session):
    """Consistency score should rise with weekly logging frequency."""
    svc = FinanceService()

    dates = [datetime.now() - timedelta(days=i * 2) for i in range(4)]
    for date in dates:
        db_session.add(
            FarmDiary(
                user_id="user_consistent", date=date, entry_type="expense",
                category="seeds", amount=1000, unit="BDT",
                notes="Regular seed purchase", crop="vegetable", plot="B",
            )
        )
    await db_session.commit()

    result = await svc.calculate_credit_score(db_session, "user_consistent")

    assert result["breakdown"]["consistency"] > 0
