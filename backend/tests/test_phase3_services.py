"""Unit tests for Phase 3 backend services."""
import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List

from app.services.community_service import (
    create_community_question,
    search_community_questions,
)
from app.services.marketplace_service import scan_product
from app.services.emergency_service import submit_claim
from app.services.ocr_service import parse_label_text


class DummyResult:
    def __init__(self, scalar: Any = None, all_values: Any = None):
        self._scalar = scalar
        self._all_values = all_values

    def scalars(self):
        return self

    def first(self):
        return self._scalar

    def all(self):
        return self._all_values

    def fetchall(self):
        return self._all_values


class DummySession:
    def __init__(self, execute_results: List[DummyResult] = None):
        self.execute_results = execute_results or []
        self.added = []
        self.committed = False
        self.refreshed = []

    async def execute(self, stmt, params=None):
        if not self.execute_results:
            return DummyResult(None)
        return self.execute_results.pop(0)

    def add(self, item):
        self.added.append(item)

    async def commit(self):
        self.committed = True

    async def refresh(self, item):
        self.refreshed.append(item)


class DummyProduct:
    def __init__(self, product_id: str, expiry_date=None):
        self.id = product_id
        self.expiry_date = expiry_date or (datetime.utcnow().date() + timedelta(days=30))


class DummyReport:
    def __init__(self):
        self.id = "report-123"
        self.status = "submitted"
        self.insurance_provider_id = None
        self.insurance_claim_id = None
        self.claimed_at = None
        self.pdf_url = None
        self.farmer_id = "farmer-xyz"
        self.crop_type = "rice"
        self.damage_cause = "flood"
        self.location_lat = 23.7
        self.location_lon = 90.35
        self.damage_estimate_percent = 40.0
        self.yield_loss_estimate_percent = 35.0
        self.voice_statement_transcribed = "Field damage after heavy rain."


@pytest.mark.asyncio
async def test_parse_label_text_extracts_fields():
    text = "Product: Super Rice Seed\nActive Ingredient: Nitrogen 18%\nNPK: 18-12-12\nExpiry Date: 2027-12-31"
    parsed = parse_label_text(text)

    assert parsed["product_name"] == "Product: Super Rice Seed"
    assert "NPK" in parsed["npk_ratio"]
    assert "Expiry" in parsed["expiry"]
    assert "Active" in parsed["active_ingredient"]


@pytest.mark.asyncio
async def test_create_community_question_commits_and_refreshes(monkeypatch):
    dummy_session = DummySession()
    question_created = []

    async def fake_commit():
        dummy_session.committed = True

    async def fake_refresh(item):
        question_created.append(item)

    def fake_encode_text(text):
        return [0.1] * 384

    dummy_session.commit = fake_commit
    dummy_session.refresh = fake_refresh
    monkeypatch.setattr("app.services.community_service.encode_text", fake_encode_text)

    question = await create_community_question(
        dummy_session,
        farmer_id_hashed="farmer-1",
        question_text="How often should I fertilize my rice?",
        crop_type="rice",
        growth_stage="vegetative",
        lat=23.78,
        lon=90.41,
        photo_url="http://example.com/photo.jpg",
    )

    assert dummy_session.committed is True
    assert question in dummy_session.added
    assert question_created[0] == question
    assert question.question_text == "How often should I fertilize my rice?"
    assert question.crop_type == "rice"
    assert question.embedding == [0.1] * 384


@pytest.mark.asyncio
async def test_search_community_questions_returns_semantic_matches(monkeypatch):
    dummy_rows = [
        {
            "id": "uuid-1",
            "question_text": "How do I protect my tomatoes from blight?",
            "crop_type": "tomato",
            "growth_stage": "flowering",
            "status": "answered",
            "created_at": datetime.utcnow(),
            "similarity": 0.82,
        }
    ]

    async def mock_query_vector_similarity(table, column, embedding, threshold, limit):
        return dummy_rows

    monkeypatch.setattr("app.services.community_service.encode_text", lambda q: [0.04] * 384)
    monkeypatch.setattr("app.services.community_service.query_vector_similarity", mock_query_vector_similarity)

    results = await search_community_questions(None, "tomato blight")
    assert len(results) == 1
    assert results[0]["crop_type"] == "tomato"
    assert results[0]["similarity"] == 0.82


@pytest.mark.asyncio
async def test_scan_product_returns_verified_for_known_barcode(monkeypatch):
    dummy_product = DummyProduct("verified-123")
    session = DummySession([DummyResult(dummy_product)])
    monkeypatch.setattr("app.services.barcode_service.decode_barcode_base64", lambda image: "12345")

    result = await scan_product(
        session,
        farmer_id_hashed="farmer-1",
        barcode="12345",
        qr_text=None,
        image_base64=None,
        lat=23.78,
        lon=90.41,
    )

    assert result["verification_result"] == "VERIFIED"
    assert result["verified_product_id"] == "verified-123"
    assert result["barcode"] == "12345"


@pytest.mark.asyncio
async def test_submit_claim_updates_report_status_and_claim_id(monkeypatch):
    report = DummyReport()
    session = DummySession([DummyResult(report)])
    monkeypatch.setattr("app.utils.pdf_generator.generate_damage_pdf", lambda report, images, output_path: output_path)

    response = await submit_claim(session, report.id, None)
    assert response["status"] == "claimed"
    assert response["insurance_claim_id"] is not None
    assert response["claimed_at"] is not None
    assert response["report_id"] == report.id
