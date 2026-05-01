from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
import json
import logging

from app.db import get_db
from app.models.db_models import FarmDiary, User
from app.crews.krishi_crew import KrishiCrewOrchestrator

logger = logging.getLogger("DiaryAPI")
router = APIRouter()

orchestrator = KrishiCrewOrchestrator()

class DiaryEntryRequest(BaseModel):
    user_id: str
    transcript: str

class DiaryEntryResponse(BaseModel):
    status: str
    extracted_data: dict
    message: str

@router.post("/add", response_model=DiaryEntryResponse)
async def add_diary_entry(
    request: DiaryEntryRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Parse a natural language text/voice transcript using the Farm Manager Agent,
    extract the structured data, and save it to the PostgreSQL database.
    """
    try:
        # Force route to Diary agent by structuring the prompt
        # We prefix it slightly to ensure the Router catches the 'diary' intent
        prompt = f"Log this transaction: {request.transcript}"
        initial_state = {
            "transcript": prompt,
            "gps": None,
            "image_path": None
        }
        
        result_state = await orchestrator.ainvoke(initial_state)
        json_str = result_state.get("reply_text", "{}")
        
        try:
            extracted = json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse diary agent output: {json_str}")
            raise HTTPException(status_code=400, detail="Could not extract structured data from input.")
            
        # Validate extracted data
        entry_type = extracted.get("entry_type", "expense")
        amount = float(extracted.get("amount", 0))
        category = extracted.get("category", "General")
        unit = extracted.get("unit", "BDT")
        notes = extracted.get("notes", request.transcript)
        
        # Save to DB
        entry = FarmDiary(
            user_id=request.user_id,
            entry_type=entry_type,
            category=category,
            amount=amount,
            unit=unit,
            notes=notes
        )
        db.add(entry)
        await db.commit()
        
        return DiaryEntryResponse(
            status="success",
            extracted_data=extracted,
            message=f"Successfully logged {entry_type} of {amount} {unit} for {category}."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding diary entry: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while logging the transaction.")


@router.get("/report")
async def get_season_report(
    user_id: str = Query(..., description="The user external ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate the total profit and loss for the user.
    """
    try:
        # Execute query to sum amounts grouped by entry_type
        result = await db.execute(
            select(
                FarmDiary.entry_type,
                func.sum(FarmDiary.amount).label("total")
            ).where(FarmDiary.user_id == user_id).group_by(FarmDiary.entry_type)
        )
        
        totals = {"expense": 0.0, "income": 0.0, "yield": 0.0}
        for row in result:
            totals[row.entry_type] = float(row.total or 0.0)
            
        profit = totals["income"] - totals["expense"]
        
        return {
            "user_id": user_id,
            "totals": totals,
            "net_profit": profit,
            "status": "Profitable" if profit > 0 else "Loss" if profit < 0 else "Break-even"
        }
        
    except Exception as e:
        logger.error(f"Error fetching diary report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while generating the report.")
