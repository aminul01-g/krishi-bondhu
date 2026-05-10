from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

from app.db import get_db
from app.models.db_models import User
from app.core.dependencies import get_current_user
from app.services.community_service import (
    create_community_question,
    get_recent_questions,
    get_question_by_id,
    search_community_questions,
    add_answer,
    upvote_answer,
    escalate_question,
)
from app.crews.krishi_crew import KrishiCrew
from app.agents.community_connector import community_connector
from crewai import Task

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
