from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.services.memory import MemoryService
from pydantic import BaseModel
from typing import List, Dict, Optional

router = APIRouter()

class MemoryFact(BaseModel):
    fact_key: str
    fact_value: str
    category: str
    confidence: float
    last_updated: str

@router.get("/{user_id}", response_model=Dict[str, List[Dict]])
async def get_farm_memory(user_id: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieve all stored facts and history for a specific farm/user.
    """
    try:
        history = await MemoryService.get_farm_history(db, user_id)
        # We also want to return structured facts
        from app.models.db_models import KnowledgeFact
        from sqlalchemy import select
        
        result = await db.execute(
            select(KnowledgeFact).where(KnowledgeFact.user_id == user_id)
        )
        facts = result.scalars().all()
        
        structured_facts = [
            {
                "key": f.fact_key,
                "value": f.fact_value,
                "category": f.category,
                "confidence": f.confidence,
                "updated_at": f.updated_at.isoformat() if f.updated_at else None
            }
            for f in facts
        ]
        
        return {
            "history": history,
            "facts": structured_facts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{user_id}/{fact_key}")
async def delete_memory_fact(user_id: str, fact_key: str, db: AsyncSession = Depends(get_db)):
    """
    Delete a specific fact from the farm memory.
    """
    from app.models.db_models import KnowledgeFact
    from sqlalchemy import delete
    
    try:
        await db.execute(
            delete(KnowledgeFact).where(
                KnowledgeFact.user_id == user_id,
                KnowledgeFact.fact_key == fact_key
            )
        )
        await db.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
