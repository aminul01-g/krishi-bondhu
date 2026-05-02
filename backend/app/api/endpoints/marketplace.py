from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from app.db import get_db
from app.services.marketplace_service import (
    create_dealer,
    list_dealers,
    get_dealer,
    add_inventory_item,
    scan_product,
    list_verified_products,
)

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
    farmer_id_hashed: str
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
async def verify_product(payload: ProductScanRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await scan_product(
            db,
            farmer_id_hashed=payload.farmer_id_hashed,
            barcode=payload.barcode,
            qr_text=payload.qr_text,
            image_base64=payload.image_base64,
            lat=payload.lat,
            lon=payload.lon,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/verified-products")
async def verified_products(limit: int = Query(25, ge=1, le=100), db: AsyncSession = Depends(get_db)):
    try:
        return await list_verified_products(db, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
