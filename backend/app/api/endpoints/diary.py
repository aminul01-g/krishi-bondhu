from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from pydantic import BaseModel
import json
import logging
import asyncio

from app.db import get_db
from app.models.db_models import FarmDiary, User
from app.core.dependencies import get_current_user
from app.crews.krishi_crew import FinancialPlanningCrew
from app.agents.farm_manager import farm_manager
from app.services.finance_service import detect_category

logger = logging.getLogger("DiaryAPI")
router = APIRouter()

class DiaryEntryRequest(BaseModel):
    transcript: str

class DiaryEntryResponse(BaseModel):
    status: str
    extracted_data: dict
    message: str

# Category Bengali label mapping
CATEGORY_LABELS = {
    "seed": "বীজ",
    "fertilizer": "সার",
    "pesticide": "কীটনাশক",
    "labor": "মজুর",
    "irrigation": "সেচ",
    "harvest": "ফলন",
    "other": "অন্যান্য",
}

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
            import re
            match = re.search(r'\{.*\}', json_str, re.DOTALL)
            if match:
                extracted = json.loads(match.group())
            else:
                extracted = json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse diary agent output: {json_str}")
            raise HTTPException(status_code=400, detail="Could not extract structured data from input. Please try again.")

        # Validate and clean extracted data
        entry_type = extracted.get("entry_type", "expense").lower()
        if entry_type not in ["income", "expense", "yield"]:
            entry_type = "expense"

        amount = float(extracted.get("amount", 0))
        unit = extracted.get("unit", "BDT")
        notes = extracted.get("notes", request.transcript)

        # Use NLP category detection — fall back to LLM result, then "other"
        detected_category = detect_category(request.transcript)
        if detected_category == "other":
            llm_cat = str(extracted.get("category", "other")).lower()
            # Map common LLM-returned English/Bengali strings to our keys
            cat_map = {
                "fertilizer": "fertilizer", "সার": "fertilizer",
                "seed": "seed", "বীজ": "seed", "চারা": "seed",
                "pesticide": "pesticide", "কীটনাশক": "pesticide",
                "labor": "labor", "মজুর": "labor", "শ্রমিক": "labor",
                "irrigation": "irrigation", "সেচ": "irrigation",
                "harvest": "harvest", "ফলন": "harvest", "income": "harvest",
            }
            detected_category = cat_map.get(llm_cat, "other")

        category = detected_category
        extracted["category"] = category
        extracted["category_label"] = CATEGORY_LABELS.get(category, "অন্যান্য")

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
            message=f"Successfully logged {entry_type} of {amount} {unit} for {CATEGORY_LABELS.get(category, category)}."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding diary entry: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while logging the transaction.")

@router.get("/entries")
async def get_diary_entries(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns paginated list of diary entries for the current user, most recent first.
    Each entry includes: id, date, text (notes), category, amount, entry_type, created_at.
    """
    try:
        user_id = current_user.external_id
        offset = (page - 1) * per_page

        stmt = (
            select(FarmDiary)
            .where(FarmDiary.user_id == user_id)
            .order_by(desc(FarmDiary.date))
            .offset(offset)
            .limit(per_page)
        )
        result = await db.execute(stmt)
        entries = result.scalars().all()

        # Total count for pagination metadata
        count_stmt = select(func.count(FarmDiary.id)).where(FarmDiary.user_id == user_id)
        count_result = await db.execute(count_stmt)
        total = count_result.scalar() or 0

        items = []
        for e in entries:
            items.append({
                "id": e.id,
                "date": e.date.isoformat() if e.date else None,
                "text": e.notes or "",
                "category": e.category or "other",
                "category_label": CATEGORY_LABELS.get(e.category or "other", "অন্যান্য"),
                "amount": float(e.amount or 0),
                "entry_type": e.entry_type or "expense",
                "unit": e.unit or "BDT",
                "created_at": e.date.isoformat() if e.date else None,
            })

        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "has_more": (offset + per_page) < total,
        }

    except Exception as e:
        logger.error(f"Error fetching diary entries: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while fetching entries.")

@router.delete("/entries/{entry_id}")
async def delete_diary_entry(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Deletes a diary entry if it belongs to the current user.
    Returns 200 OK on success, 404 if not found or unauthorized.
    """
    try:
        user_id = current_user.external_id
        stmt = select(FarmDiary).where(
            (FarmDiary.id == entry_id) & (FarmDiary.user_id == user_id)
        )
        result = await db.execute(stmt)
        entry = result.scalar_one_or_none()

        if entry is None:
            raise HTTPException(status_code=404, detail="Entry not found.")

        await db.delete(entry)
        await db.commit()

        return {"status": "deleted", "id": entry_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting diary entry {entry_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while deleting the entry.")

@router.get("/report")
async def get_season_report(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate the total profit and loss for the user.
    Also includes expense breakdown by category (top categories by spend).
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

        # Category breakdown (expenses only)
        cat_result = await db.execute(
            select(
                FarmDiary.category,
                func.sum(FarmDiary.amount).label("total")
            ).where(
                (FarmDiary.user_id == user_id) & (FarmDiary.entry_type == "expense")
            ).group_by(FarmDiary.category)
            .order_by(desc(func.sum(FarmDiary.amount)))
            .limit(5)
        )

        category_breakdown = []
        for row in cat_result:
            cat_key = row.category or "other"
            category_breakdown.append({
                "category": cat_key,
                "label": CATEGORY_LABELS.get(cat_key, "অন্যান্য"),
                "amount": float(row.total or 0.0),
            })

        return {
            "user_id": user_id,
            "totals": totals,
            "net_profit": profit,
            "status": "Profitable" if profit > 0 else "Loss" if profit < 0 else "Break-even",
            "category_breakdown": category_breakdown,
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
        stmt = select(FarmDiary).where(FarmDiary.user_id == user_id).order_by(FarmDiary.date.desc())
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
            pdf.cell(40, 10, text=str(entry.date.date()), border=1)
            pdf.cell(30, 10, text=entry.entry_type.capitalize(), border=1)
            pdf.cell(40, 10, text=entry.category or "", border=1)
            pdf.cell(30, 10, text=f"{entry.amount} {entry.unit}", border=1)
            pdf.cell(50, 10, text=entry.notes[:25] + "..." if entry.notes and len(entry.notes) > 25 else (entry.notes or ""), border=1, new_x="LMARGIN", new_y="NEXT")

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
