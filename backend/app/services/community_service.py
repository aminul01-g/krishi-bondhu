"""Community Q&A and expert escalation service helpers."""

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime
import uuid

from app.models.community_models import (
    CommunityQuestion,
    CommunityAnswer,
    AnswerUpvote,
    EscalationQueue,
)
from app.services.embedding_service import encode_text
from app.utils.vector_utils import query_vector_similarity
from app.services.geospatial_service import find_nearest_experts


def _serialize_question(question: CommunityQuestion) -> dict:
    return {
        "id": str(question.id),
        "farmer_id_hashed": question.farmer_id_hashed,
        "question_text": question.question_text,
        "crop_type": question.crop_type,
        "growth_stage": question.growth_stage,
        "photo_url": question.photo_url,
        "lat": question.lat,
        "lon": question.lon,
        "status": question.status,
        "moderation_flag": question.moderation_flag,
        "is_archived": question.is_archived,
        "admin_review_needed": question.admin_review_needed,
        "created_at": question.created_at.isoformat() if question.created_at else None,
        "updated_at": question.updated_at.isoformat() if question.updated_at else None,
    }


def _serialize_answer(answer: CommunityAnswer) -> dict:
    return {
        "id": str(answer.id),
        "question_id": str(answer.question_id),
        "answerer_id": answer.answerer_id,
        "answerer_name": answer.answerer_name,
        "answerer_credentials": answer.answerer_credentials,
        "answer_text": answer.answer_text,
        "is_expert_answer": answer.is_expert_answer,
        "is_verified": answer.is_verified,
        "created_at": answer.created_at.isoformat() if answer.created_at else None,
        "verified_at": answer.verified_at.isoformat() if answer.verified_at else None,
    }


async def create_community_question(
    session: AsyncSession,
    farmer_id_hashed: str,
    question_text: str,
    crop_type: str,
    growth_stage: Optional[str],
    lat: float,
    lon: float,
    photo_url: Optional[str] = None,
) -> CommunityQuestion:
    embedding = encode_text(question_text)
    question = CommunityQuestion(
        farmer_id_hashed=farmer_id_hashed,
        question_text=question_text,
        crop_type=crop_type,
        growth_stage=growth_stage,
        photo_url=photo_url,
        lat=lat,
        lon=lon,
        location_geom=f"POINT({lon} {lat})",
        embedding=embedding,
    )
    session.add(question)
    await session.commit()
    await session.refresh(question)
    return question


async def get_recent_questions(session: AsyncSession, limit: int = 20) -> List[dict]:
    from sqlalchemy import select

    result = await session.execute(
        select(CommunityQuestion).order_by(CommunityQuestion.created_at.desc()).limit(limit)
    )
    return [_serialize_question(row) for row in result.scalars().all()]


async def get_question_by_id(session: AsyncSession, question_id: str) -> Optional[dict]:
    from sqlalchemy import select

    result = await session.execute(
        select(CommunityQuestion).where(CommunityQuestion.id == question_id)
    )
    question = result.scalars().first()
    return _serialize_question(question) if question else None


async def search_community_questions(session: AsyncSession, query: str, limit: int = 10):
    query_embedding = encode_text(query)
    rows = await query_vector_similarity("community_questions", "embedding", query_embedding, threshold=0.6, limit=limit)
    results = []
    for row in rows:
        results.append({
            "id": str(row["id"]),
            "question_text": row["question_text"],
            "crop_type": row["crop_type"],
            "growth_stage": row["growth_stage"],
            "status": row["status"],
            "similarity": float(row["similarity"]),
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        })
    return results


async def add_answer(
    session: AsyncSession,
    question_id: str,
    answerer_id: str,
    answerer_name: str,
    answer_text: str,
    answerer_credentials: Optional[str] = None,
    is_expert_answer: bool = False,
) -> CommunityAnswer:
    answer = CommunityAnswer(
        question_id=question_id,
        answerer_id=answerer_id,
        answerer_name=answerer_name,
        answerer_credentials=answerer_credentials,
        answer_text=answer_text,
        is_expert_answer=is_expert_answer,
    )
    session.add(answer)
    await session.commit()
    await session.refresh(answer)
    return answer


async def upvote_answer(
    session: AsyncSession,
    answer_id: str,
    farmer_id_hashed: str,
    rating: Optional[int] = None,
) -> AnswerUpvote:
    from sqlalchemy import select

    existing = await session.execute(
        select(AnswerUpvote)
        .where(AnswerUpvote.answer_id == answer_id)
        .where(AnswerUpvote.farmer_id_hashed == farmer_id_hashed)
    )
    if existing.scalars().first():
        raise ValueError("Farmer has already voted for this answer")

    upvote = AnswerUpvote(
        answer_id=answer_id,
        farmer_id_hashed=farmer_id_hashed,
        rating=rating,
    )
    session.add(upvote)
    await session.commit()
    await session.refresh(upvote)
    return upvote


async def escalate_question(
    session: AsyncSession,
    question_id: str,
    lat: float,
    lon: float,
    automatic: bool = True,
) -> EscalationQueue:
    experts = await find_nearest_experts(lat, lon, limit=1)
    expert_id = experts[0]["id"] if experts else None
    escalation = EscalationQueue(
        question_id=question_id,
        expert_id=expert_id,
        status="assigned" if expert_id else "pending",
        created_at=datetime.utcnow(),
        assigned_at=datetime.utcnow() if expert_id else None,
        auto_escalate_at=datetime.utcnow(),
    )
    session.add(escalation)
    await session.commit()
    await session.refresh(escalation)
    return escalation
