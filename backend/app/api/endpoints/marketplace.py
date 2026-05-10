from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date
import asyncio
import logging

from app.db import get_db
from app.models.db_models import User
from app.core.dependencies import get_current_user
from app.services.marketplace_service import (
    create_dealer,
    list_dealers,
    get_dealer,
    add_inventory_item,
    scan_product,
    list_verified_products,
)
from app.crews.krishi_crew import MarketAnalysisCrew
from app.agents.procurement_advisor import procurement_advisor
from crewai import Task

logger = logging.getLogger(__name__)
router = APIRouter()

class DealerCreate(BaseModel):
    name: str
    phone_number: str
    email: Optional[str] = None
    location_lat: float
    location_lon: float
    regions_served: Optional[List[str]] = Field(default_factory=list)

class InventoryCreate(BaseModel):
    product_name: str
    input_type: str
    crop_type: Optional[str] = None
    batch_number: Optional[str] = None
    manufacturer: Optional[str] = None
    quantity_in_stock: int
    price_bdt: float
    expiry_date: date

class ProductScanRequest(BaseModel):
    barcode: Optional[str] = None
    qr_text: Optional[str] = None
    image_base64: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None

@router.post("/dealers")
async def register_dealer(payload: DealerCreate, db: AsyncSession = Depends(get_db)):
    try:
        dealer = await create_dealer(
            db,
            name=payload.name,
            phone_number=payload.phone_number,
            email=payload.email,
            location_lat=payload.location_lat,
            location_lon=payload.location_lon,
            regions_served=payload.regions_served,
        )
        return {"id": str(dealer.id), "name": dealer.name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dealers")
async def find_dealers(
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await list_dealers(db, lat=lat, lon=lon, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dealers/{dealer_id}")
async def retrieve_dealer(dealer_id: str, db: AsyncSession = Depends(get_db)):
    dealer = await get_dealer(db, dealer_id)
    if not dealer:
        raise HTTPException(status_code=404, detail="Dealer not found")
    return dealer

@router.post("/dealers/{dealer_id}/inventory")
async def add_dealer_inventory(dealer_id: str, payload: InventoryCreate, db: AsyncSession = Depends(get_db)):
    try:
        item = await add_inventory_item(
            db,
            dealer_id=dealer_id,
            product_name=payload.product_name,
            input_type=payload.input_type,
            crop_type=payload.crop_type,
            batch_number=payload.batch_number,
            manufacturer=payload.manufacturer,
            quantity_in_stock=payload.quantity_in_stock,
            price_bdt=payload.price_bdt,
            expiry_date=payload.expiry_date,
        )
        return {"id": str(item.id), "product_name": item.product_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scan")
async def verify_product(
    payload: ProductScanRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    AI-Powered Product Verification.
    Combines raw scan results with ProcurementAdvisor's reasoning to warn about fakes.
    """
    try:
        # 1. Get raw verification result from service
        scan_result = await scan_product(
            db,
            farmer_id_hashed=current_user.external_id,
            barcode=payload.barcode,
            qr_text=payload.qr_text,
            image_base64=payload.image_base64,
            lat=payload.lat,
            lon=payload.lon,
        )

        # 2. Use specialized MarketAnalysisCrew to interpret the result and provide a warning/advice
        verify_task = Task(
            description=(
                f"Interpret the product scan result: {scan_result}. "
                "If the product is unverified or suspected fake, explain the risks clearly "
                "and suggest a verified local dealer nearby."
            ),
            expected_output="A clear verdict (Verified/Suspected/Unknown) with detailed advice on product authenticity and local alternatives.",
            agent=procurement_advisor
        )

        crew_obj = MarketAnalysisCrew()
        crew = crew_obj.create_crew(tasks=[verify_task])

        inputs = {
            "user_input": "Is this product authentic?",
            "scan_data": scan_result,
            "user_id": current_user.external_id
        }

        ai_verdict = await asyncio.to_thread(crew.kickoff, inputs=inputs)

        import uuid
        scan_id = scan_result.get("scan_id")
        if not scan_id:
            scan_id = str(uuid.uuid4())
            scan_result["scan_id"] = scan_id

        return {
            "scan_result": scan_result,
            "ai_verdict": str(ai_verdict)
        }
    except Exception as e:
        logger.error(f"Product verification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/verified-products")
async def verified_products(limit: int = Query(25, ge=1, le=100), db: AsyncSession = Depends(get_db)):
    try:
        return await list_verified_products(db, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
