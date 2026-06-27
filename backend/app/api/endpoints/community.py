from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import asyncio
import logging

from app.db import get_db
from app.models.db_models import User, FarmerProfile
from app.core.dependencies import get_current_user
from app.services.community_service import (
    create_community_question,
    get_recent_questions,
    get_question_by_id,
    search_community_questions,
    add_answer,
    upvote_answer,
    escalate_question,
    list_posts,
    get_post_detail,
    toggle_question_upvote,
    can_generate_ai_answer,
    save_ai_answer,
)
from app.utils.profile_context import get_farmer_context
from app.crews.krishi_crew import KrishiCrew
from app.agents.community_connector import community_connector
from crewai import Task

logger = logging.getLogger(__name__)
router = APIRouter()

class CommunityQuestionCreate(BaseModel):
    question_text: str
    crop_type: str
    growth_stage: Optional[str]
    lat: float
    lon: float
    photo_url: Optional[str] = None

class CommunityAnswerCreate(BaseModel):
    answerer_id: str
    answerer_name: str
    answer_text: str
    answerer_credentials: Optional[str] = None
    is_expert_answer: bool = False

class CommunityUpvoteCreate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)

class EscalateRequest(BaseModel):
    lat: float
    lon: float


# --- New /posts surface (discovery + trust signals + AI answers) ------------

class PostCreate(BaseModel):
    question_text: str
    crop_type: str
    growth_stage: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    district: Optional[str] = None  # Falls back to the farmer's profile district
    photo_url: Optional[str] = None

class PostReplyCreate(BaseModel):
    answer_text: str


async def _resolve_district(db: AsyncSession, current_user: User, override: Optional[str]) -> Optional[str]:
    """Prefer the explicitly supplied district, else fall back to the profile."""
    if override:
        return override
    try:
        result = await db.execute(
            select(FarmerProfile).where(FarmerProfile.user_id == current_user.id)
        )
        profile = result.scalars().first()
        return profile.district if profile else None
    except Exception:
        return None


@router.get("/posts")
async def list_posts_endpoint(
    district: Optional[str] = Query(None),
    crop: Optional[str] = Query(None),
    sort: str = Query("new", pattern="^(top|new)$"),
    page: int = Query(1, ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await list_posts(
            db,
            district=district,
            crop=crop,
            sort=sort,
            page=page,
            viewer_id=current_user.external_id,
        )
    except Exception:
        logger.exception("Listing community posts failed")
        raise HTTPException(status_code=500, detail="Failed to list posts")


@router.post("/posts")
async def create_post(
    payload: PostCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a community post. District falls back to the farmer profile; coords
    fall back to a sensible Bangladesh default when the client has no GPS yet."""
    try:
        district = await _resolve_district(db, current_user, payload.district)
        lat = payload.lat if payload.lat is not None else 23.81
        lon = payload.lon if payload.lon is not None else 90.41

        question = await create_community_question(
            db,
            farmer_id_hashed=current_user.external_id,
            question_text=payload.question_text,
            crop_type=payload.crop_type,
            growth_stage=payload.growth_stage,
            lat=lat,
            lon=lon,
            photo_url=payload.photo_url,
            district=district,
        )
        return {"id": str(question.id), "status": question.status, "district": question.district}
    except Exception:
        logger.exception("Community post creation failed")
        raise HTTPException(status_code=500, detail="Failed to create post")


@router.get("/posts/{post_id}")
async def get_post(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    post = await get_post_detail(db, post_id, viewer_id=current_user.external_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.post("/posts/{post_id}/upvote")
async def upvote_post(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Toggle the current user's upvote on a post."""
    try:
        return await toggle_question_upvote(db, post_id, current_user.external_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        logger.exception("Toggling post upvote failed")
        raise HTTPException(status_code=500, detail="Failed to upvote post")


@router.post("/posts/{post_id}/answers")
async def reply_to_post(
    post_id: str,
    payload: PostReplyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reply as a human (the authenticated farmer)."""
    try:
        # Ensure the post exists first for a clean 404.
        existing = await get_post_detail(db, post_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Post not found")

        answer = await add_answer(
            db,
            question_id=post_id,
            answerer_id=current_user.external_id,
            answerer_name=current_user.username,
            answer_text=payload.answer_text,
        )
        return {"id": str(answer.id), "question_id": str(answer.question_id)}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Replying to community post failed")
        raise HTTPException(status_code=500, detail="Failed to post reply")


@router.post("/posts/{post_id}/ai_answer")
async def generate_post_ai_answer(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate (and persist) an AI answer for a post using the CrewAI setup.

    Rate limited to 1 generation per post per hour. Injects the post text plus
    district context (the asking farmer's profile) so the answer is local-aware.
    Returns the saved AI answer.
    """
    # 1. Cooldown check (DB-level, survives restarts).
    allowed, retry_after = await can_generate_ai_answer(db, post_id)
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": "AI answer already generated recently. Try again later.", "retry_after": retry_after},
            headers={"Retry-After": str(retry_after)},
        )

    # 2. Load post + district context.
    post = await get_post_detail(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    district_context = await get_farmer_context(current_user.id, db)

    # 3. Build the CrewAI task — same setup as the rest of the community module.
    location_hint = f" (asked from district: {post.get('district')})" if post.get("district") else ""
    profile_hint = f"\n\nAsking farmer's context: {district_context}" if district_context else ""
    answer_task = Task(
        description=(
            f"A Bangladeshi farmer asked the following farming question in Bengali. "
            f"Provide a clear, practical, and locally relevant answer in Bengali. "
            f"Keep it concise (3-5 sentences) and actionable.\n\n"
            f"Question: \"{post.get('question_text')}\"{location_hint}{profile_hint}"
        ),
        expected_output="A helpful farming answer in Bengali, 3-5 sentences, practical and actionable.",
        agent=community_connector,
    )

    crew_obj = KrishiCrew()
    crew = crew_obj.create_crew(tasks=[answer_task])
    inputs = {"user_input": post.get("question_text", ""), "user_id": current_user.external_id}

    try:
        result = await asyncio.to_thread(crew.kickoff, inputs=inputs)
    except Exception:
        logger.exception("CrewAI answer generation failed for post %s", post_id)
        raise HTTPException(status_code=503, detail="AI answer could not be generated right now")

    ai_answer_text = str(result).strip()

    # 4. Persist + return.
    saved = await save_ai_answer(db, post_id, ai_answer_text)
    if not saved:
        raise HTTPException(status_code=404, detail="Post not found")
    return {"ai_answer": ai_answer_text, "post": saved}


# --- Legacy /questions surface (unchanged) ----------------------------------

@router.post("/questions")
async def submit_question(
    payload: CommunityQuestionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        # Use AI to enrich the question metadata before saving
        enrich_task = Task(
            description=f"Analyze this farming question: '{payload.question_text}'. Categorize it and suggest 3 relevant keywords for better community discovery.",
            expected_output="A JSON object with 'category' and 'keywords' (list of strings).",
            agent=community_connector
        )

        crew_obj = KrishiCrew()
        crew = crew_obj.create_crew(tasks=[enrich_task])

        inputs = {"user_input": payload.question_text, "user_id": current_user.external_id}
        ai_metadata = await asyncio.to_thread(crew.kickoff, inputs=inputs)

        question = await create_community_question(
            db,
            farmer_id_hashed=current_user.external_id,
            question_text=payload.question_text,
            crop_type=payload.crop_type,
            growth_stage=payload.growth_stage,
            lat=payload.lat,
            lon=payload.lon,
            photo_url=payload.photo_url,
        )
        return {"id": str(question.id), "status": question.status, "ai_insights": str(ai_metadata)}
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Community question submission failed")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/questions")
async def list_questions(
    query: Optional[str] = Query(None, description="Search query for semantic community question matching"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    try:
        if query:
            return await search_community_questions(db, query, limit=limit)
        return await get_recent_questions(db, limit=limit)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Listing community questions failed")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/questions/{question_id}")
async def get_question(question_id: str, db: AsyncSession = Depends(get_db)):
    question = await get_question_by_id(db, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question

@router.post("/questions/{question_id}/answers")
async def answer_question(question_id: str, payload: CommunityAnswerCreate, db: AsyncSession = Depends(get_db)):
    try:
        answer = await add_answer(
            db,
            question_id=question_id,
            answerer_id=payload.answerer_id,
            answerer_name=payload.answerer_name,
            answer_text=payload.answer_text,
            answerer_credentials=payload.answerer_credentials,
            is_expert_answer=payload.is_expert_answer,
        )
        return {"id": str(answer.id), "question_id": str(answer.question_id)}
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Answering community question failed")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/answers/{answer_id}/upvote")
async def upvote_answer_endpoint(
    answer_id: str,
    payload: CommunityUpvoteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        upvote = await upvote_answer(db, answer_id, current_user.external_id, payload.rating)
        return {"id": str(upvote.id), "rating": upvote.rating}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/questions/{question_id}/escalate")
async def escalate_question_endpoint(question_id: str, payload: EscalateRequest, db: AsyncSession = Depends(get_db)):
    try:
        # Use AI to summarize the case before escalating to a human expert
        from crewai import Task
        summary_task = Task(
            description=f"Summarize the core issue for question ID {question_id} and explain why it requires urgent expert attention based on location ({payload.lat}, {payload.lon}).",
            expected_output="A concise 2-sentence escalation summary for an agricultural extension officer.",
            agent=community_connector
        )

        crew_obj = KrishiCrew()
        crew = crew_obj.create_crew(tasks=[summary_task])

        inputs = {"user_input": f"Escalate question {question_id}", "gps": {"lat": payload.lat, "lon": payload.lon}}
        summary_text = await asyncio.to_thread(crew.kickoff, inputs=inputs)

        escalation = await escalate_question(db, question_id, payload.lat, payload.lon)
        return {"escalation_id": str(escalation.id), "status": escalation.status, "ai_summary": str(summary_text)}
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Escalating question failed")
        raise HTTPException(status_code=500, detail=str(e))
