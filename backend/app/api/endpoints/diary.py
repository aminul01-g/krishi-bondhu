from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
import json
import logging
import asyncio

from app.db import get_db
from app.models.db_models import FarmDiary, User
from app.core.dependencies import get_current_user
from app.crews.krishi_crew import FinancialPlanningCrew
from app.agents.farm_manager import farm_manager

logger = logging.getLogger("DiaryAPI")
router = APIRouter()

class DiaryEntryRequest(BaseModel):
    transcript: str

class DiaryEntryResponse(BaseModel):
    status: str
    extracted_data: dict
    message: str

@router.post("/add", response_model=DiaryEntryResponse)
async def add_diary_entry(
    request: DiaryEntryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Parse a natural language text/voice transcript using the Farm Manager Agent,
    extract the structured data, and save it to the PostgreSQL database.
    """
    try:
        # Use specialized FinancialPlanningCrew for diary management
        from crewai import Task

        diary_task = Task(
            description=f"Analyze the following farm transaction: '{request.transcript}'. Extract the entry type (income/expense/yield), amount, unit, category, and a concise note. Output the result in valid JSON format.",
            expected_output="A JSON object with keys: 'entry_type', 'amount', 'unit', 'category', 'notes'.",
            agent=farm_manager
        )

        crew_obj = FinancialPlanningCrew()
        crew = crew_obj.create_crew(tasks=[diary_task])

        inputs = {
            "user_input": request.transcript,
            "user_id": current_user.external_id
        }

        # Execute the crew
        result_str = await asyncio.to_thread(crew.kickoff, inputs=inputs)

        # Clean JSON from LLM output
        json_str = str(result_str).replace("```json", "").replace("```", "").strip()

        try:
            extracted = json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse diary agent output: {json_str}")
            raise HTTPException(status_code=400, detail="Could not extract structured data from input. Please try again.")

        # Validate and clean extracted data
        entry_type = extracted.get("entry_type", "expense").lower()
        if entry_type not in ["income", "expense", "yield"]:
            entry_type = "expense"

        amount = float(extracted.get("amount", 0))
        category = extracted.get("category", "General")
        unit = extracted.get("unit", "BDT")
        notes = extracted.get("notes", request.transcript)

        # Save to DB
        entry = FarmDiary(
            user_id=current_user.external_id,
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate the total profit and loss for the user.
    """
    try:
        user_id = current_user.external_id
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
    current_user: User = Depends(get_current_user),
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
        user_id = current_user.external_id
        stmt = select(FarmDiary).where(FarmDiary.user_id == user_id).order_by(FarmDiary.created_at.desc())
        result = await db.execute(stmt)
        entries = result.scalars().all()

        if not entries:
            return JSONResponse(content={"message": "No diary entries found for this user. Log some transactions first!"}, status_code=404)

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("helvetica", 'B', 16)
        pdf.cell(0, 10, text="KrishiBondhu - Digital Farm Record", new_x="LMARGIN", new_y="NEXT", align='C')
        pdf.set_font("helvetica", size=10)
        pdf.cell(0, 10, text=f"Official Financial Audit for Farmer ID: {user_id}", new_x="LMARGIN", new_y="NEXT", align='C')
        pdf.ln(10)

        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("helvetica", 'B', 10)
        pdf.cell(40, 10, "Date", 1, 0, 'C', 1)
        pdf.cell(30, 10, "Type", 1, 0, 'C', 1)
        pdf.cell(40, 10, "Category", 1, 0, 'C', 1)
        pdf.cell(30, 10, "Amount", 1, 0, 'C', 1)
        pdf.cell(50, 10, "Notes", 1, 1, 'C', 1)

        pdf.set_font("helvetica", size=9)
        for entry in entries:
            pdf.cell(40, 10, text=str(entry.created_at.date()), border=1)
            pdf.cell(30, 10, text=entry.entry_type.capitalize(), border=1)
            pdf.cell(40, 10, text=entry.category, border=1)
            pdf.cell(30, 10, text=f"{entry.amount} {entry.unit}", border=1)
            pdf.cell(50, 10, text=entry.notes[:25] + "..." if len(entry.notes) > 25 else entry.notes, border=1, new_x="LMARGIN", new_y="NEXT")

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
