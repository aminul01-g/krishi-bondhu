"""Community Q&A and expert escalation service helpers."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from datetime import datetime, timedelta
import uuid

from app.models.community_models import (
    CommunityQuestion,
    CommunityAnswer,
    AnswerUpvote,
    QuestionUpvote,
    EscalationQueue,
)
from app.services.embedding_service import encode_text
from app.utils.vector_utils import query_vector_similarity
from app.services.geospatial_service import find_nearest_experts

# The four crops that get dedicated filter chips. Anything else is bucketed
# under the "অন্যান্য" (Other) chip on the frontend.
NAMED_CROPS = ["ধান", "গম", "আলু", "পাট"]

PAGE_SIZE = 20


def _serialize_question(question: CommunityQuestion, upvoted_by_me: bool = False) -> dict:
    return {
        "id": str(question.id),
        "farmer_id_hashed": question.farmer_id_hashed,
        "question_text": question.question_text,
        "crop_type": question.crop_type,
        "growth_stage": question.growth_stage,
        "district": question.district,
        "photo_url": question.photo_url,
        "lat": question.lat,
        "lon": question.lon,
        "status": question.status,
        "moderation_flag": question.moderation_flag,
        "is_archived": question.is_archived,
        "admin_review_needed": question.admin_review_needed,
        "ai_answer": question.ai_answer,
        "ai_answer_generated_at": question.ai_answer_generated_at.isoformat() if question.ai_answer_generated_at else None,
        "upvotes_count": question.upvotes_count or 0,
        "answers_count": question.answers_count or 0,
        "upvoted_by_me": upvoted_by_me,
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
    district: Optional[str] = None,
) -> CommunityQuestion:
    embedding = encode_text(question_text)
    question = CommunityQuestion(
        farmer_id_hashed=farmer_id_hashed,
        question_text=question_text,
        crop_type=crop_type,
        growth_stage=growth_stage,
        district=district,
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


async def list_posts(
    session: AsyncSession,
    district: Optional[str] = None,
    crop: Optional[str] = None,
    sort: str = "new",
    page: int = 1,
    viewer_id: Optional[str] = None,
) -> dict:
    """Discovery feed: filter by district/crop, sort new|top, paginate.

    Returns {"posts": [...], "page": int, "has_more": bool}.
    """
    stmt = select(CommunityQuestion).where(CommunityQuestion.is_archived.is_(False))

    if district:
        stmt = stmt.where(CommunityQuestion.district == district)

    if crop:
        if crop == "অন্যান্য":
            # The "Other" chip: everything that isn't one of the named crops.
            stmt = stmt.where(CommunityQuestion.crop_type.notin_(NAMED_CROPS))
        else:
            stmt = stmt.where(CommunityQuestion.crop_type == crop)

    if sort == "top":
        # Popular first; break ties with recency so the feed never feels stale.
        stmt = stmt.order_by(
            CommunityQuestion.upvotes_count.desc().nullslast(),
            CommunityQuestion.created_at.desc(),
        )
    else:
        stmt = stmt.order_by(CommunityQuestion.created_at.desc())

    offset = max(page - 1, 0) * PAGE_SIZE
    stmt = stmt.offset(offset).limit(PAGE_SIZE + 1)  # +1 to cheaply detect next page

    result = await session.execute(stmt)
    rows = result.scalars().all()
    has_more = len(rows) > PAGE_SIZE
    rows = rows[:PAGE_SIZE]

    return {
        "posts": [_serialize_question(q, await _did_upvote(session, q.id, viewer_id)) for q in rows],
        "page": page,
        "has_more": has_more,
    }


async def _did_upvote(session: AsyncSession, question_id, viewer_id: Optional[str]) -> bool:
    """Whether the current viewer has upvoted this post (for toggle UI state)."""
    if not viewer_id:
        return False
    res = await session.execute(
        select(QuestionUpvote.id)
        .where(QuestionUpvote.question_id == question_id)
        .where(QuestionUpvote.farmer_id_hashed == viewer_id)
    )
    return res.scalars().first() is not None


async def get_post_detail(session: AsyncSession, post_id: str, viewer_id: Optional[str] = None) -> Optional[dict]:
    """Single post + AI answer + human answers + viewer's upvote state."""
    result = await session.execute(
        select(CommunityQuestion).where(CommunityQuestion.id == post_id)
    )
    question = result.scalars().first()
    if not question:
        return None

    answers = await session.execute(
        select(CommunityAnswer)
        .where(CommunityAnswer.question_id == post_id)
        .order_by(CommunityAnswer.is_expert_answer.desc(), CommunityAnswer.created_at.asc())
    )
    return {
        **_serialize_question(question, await _did_upvote(session, question.id, viewer_id)),
        "answers": [_serialize_answer(a) for a in answers.scalars().all()],
    }


async def toggle_question_upvote(session: AsyncSession, post_id: str, farmer_id_hashed: str) -> dict:
    """Toggle a post upvote. Returns {"upvoted": bool, "upvotes_count": int}."""
    result = await session.execute(
        select(CommunityQuestion).where(CommunityQuestion.id == post_id)
    )
    question = result.scalars().first()
    if not question:
        raise ValueError("Post not found")

    existing = await session.execute(
        select(QuestionUpvote)
        .where(QuestionUpvote.question_id == post_id)
        .where(QuestionUpvote.farmer_id_hashed == farmer_id_hashed)
    )
    existing_vote = existing.scalars().first()

    if existing_vote:
        await session.delete(existing_vote)
        question.upvotes_count = max((question.upvotes_count or 0) - 1, 0)
        upvoted = False
    else:
        session.add(QuestionUpvote(question_id=post_id, farmer_id_hashed=farmer_id_hashed))
        question.upvotes_count = (question.upvotes_count or 0) + 1
        upvoted = True

    await session.commit()
    return {"upvoted": upvoted, "upvotes_count": question.upvotes_count or 0}


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
    # Keep the denormalized answers_count in sync.
    q_result = await session.execute(
        select(CommunityQuestion).where(CommunityQuestion.id == question_id)
    )
    question = q_result.scalars().first()
    if question:
        question.answers_count = (question.answers_count or 0) + 1
        if question.status == "pending":
            question.status = "answered"
    await session.commit()
    await session.refresh(answer)
    return answer


# --- AI answer generation: persistence + rate limiting ----------------------
#
# The rate limit is "1 generation per post per hour" — enforced here at the DB
# layer via ai_answer_generated_at so it survives restarts and works across
# processes (no in-memory state to lose). can_generate_ai_answer() returns
# (allowed, retry_after_seconds); the endpoint turns a "not allowed" into HTTP 429.
AI_ANSWER_COOLDOWN = timedelta(hours=1)


async def can_generate_ai_answer(session: AsyncSession, post_id: str) -> tuple:
    """(allowed: bool, retry_after_seconds: int)."""
    result = await session.execute(
        select(CommunityQuestion.ai_answer_generated_at).where(CommunityQuestion.id == post_id)
    )
    generated_at = result.scalars().first()
    if not generated_at:
        return True, 0
    elapsed = datetime.utcnow() - generated_at
    if elapsed >= AI_ANSWER_COOLDOWN:
        return True, 0
    retry_after = int((AI_ANSWER_COOLDOWN - elapsed).total_seconds())
    return False, max(retry_after, 1)


async def save_ai_answer(session: AsyncSession, post_id: str, ai_answer: str) -> Optional[dict]:
    """Persist a freshly generated AI answer and return the updated serialization."""
    result = await session.execute(
        select(CommunityQuestion).where(CommunityQuestion.id == post_id)
    )
    question = result.scalars().first()
    if not question:
        return None
    question.ai_answer = ai_answer
    question.ai_answer_generated_at = datetime.utcnow()
    if question.status == "pending":
        question.status = "answered"
    await session.commit()
    await session.refresh(question)
    return _serialize_question(question)


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
    experts = await find_nearest_experts(session, lat, lon, limit=1)
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
