from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
import json
import logging

from app.db import get_db
from app.models.db_models import FarmDiary, User
# from app.crews.krishi_crew import KrishiCrewOrchestrator  # Lazy import to avoid circular deps
from app.core.dependencies import orchestrator

logger = logging.getLogger("DiaryAPI")
router = APIRouter()

# orchestrator = KrishiCrewOrchestrator()  # Lazy import to avoid circular deps

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
        
        # Mock Inventory Update Logic
        if "bought" in request.transcript.lower() or "purchase" in request.transcript.lower():
            logger.info(f"Inventory: Incrementing stock for {category} by {amount} units.")
        elif "used" in request.transcript.lower() or "applied" in request.transcript.lower():
            logger.info(f"Inventory: Decrementing stock for {category} by {amount} units.")
        
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


@router.get("/export/pdf")
async def export_diary_pdf(
    user_id: str = Query(..., description="The user external ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Generates a professional PDF financial report for bank loan applications.
    """
    from fpdf import FPDF
    import tempfile
    from fastapi.responses import FileResponse
    import os

    try:
        # Fetch entries
        stmt = select(FarmDiary).where(FarmDiary.user_id == user_id).order_by(FarmDiary.created_at.desc())
        result = await db.execute(stmt)
        entries = result.scalars().all()

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, txt="KrishiBondhu - Digital Farm Record", ln=True, align='C')
        pdf.set_font("Arial", size=10)
        pdf.cell(200, 10, txt=f"Official Financial Audit for Farmer ID: {user_id}", ln=True, align='C')
        pdf.ln(10)

        # Table Header
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(40, 10, "Date", 1, 0, 'C', 1)
        pdf.cell(30, 10, "Type", 1, 0, 'C', 1)
        pdf.cell(40, 10, "Category", 1, 0, 'C', 1)
        pdf.cell(30, 10, "Amount", 1, 0, 'C', 1)
        pdf.cell(50, 10, "Notes", 1, 1, 'C', 1)

        pdf.set_font("Arial", size=9)
        for entry in entries:
            pdf.cell(40, 10, str(entry.created_at.date()), 1)
            pdf.cell(30, 10, entry.entry_type.capitalize(), 1)
            pdf.cell(40, 10, entry.category, 1)
            pdf.cell(30, 10, f"{entry.amount} {entry.unit}", 1)
            pdf.cell(50, 10, entry.notes[:25] + "..." if len(entry.notes) > 25 else entry.notes, 1, 1)

        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        pdf.output(temp.name)
        
        return FileResponse(
            path=temp.name, 
            filename=f"KrishiBondhu_Report_{user_id}.pdf",
            media_type="application/pdf"
        )

    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate PDF report.")
