from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.services.community_service import (
    create_community_question,
    get_recent_questions,
    get_question_by_id,
    search_community_questions,
    add_answer,
    upvote_answer,
    escalate_question,
)

router = APIRouter()


class CommunityQuestionCreate(BaseModel):
    farmer_id_hashed: str
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
    farmer_id_hashed: str
    rating: Optional[int] = Field(None, ge=1, le=5)


class EscalateRequest(BaseModel):
    lat: float
    lon: float


@router.post("/questions")
async def submit_question(payload: CommunityQuestionCreate, db: AsyncSession = Depends(get_db)):
    try:
        question = await create_community_question(
            db,
            farmer_id_hashed=payload.farmer_id_hashed,
            question_text=payload.question_text,
            crop_type=payload.crop_type,
            growth_stage=payload.growth_stage,
            lat=payload.lat,
            lon=payload.lon,
            photo_url=payload.photo_url,
        )
        return {"id": str(question.id), "status": question.status}
    except Exception as e:
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
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/answers/{answer_id}/upvote")
async def upvote_answer_endpoint(answer_id: str, payload: CommunityUpvoteCreate, db: AsyncSession = Depends(get_db)):
    try:
        upvote = await upvote_answer(db, answer_id, payload.farmer_id_hashed, payload.rating)
        return {"id": str(upvote.id), "rating": upvote.rating}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/questions/{question_id}/escalate")
async def escalate_question_endpoint(question_id: str, payload: EscalateRequest, db: AsyncSession = Depends(get_db)):
    try:
        escalation = await escalate_question(db, question_id, payload.lat, payload.lon)
        return {"escalation_id": str(escalation.id), "status": escalation.status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
