"""Marketplace and product verification service helpers."""

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime
import uuid

from app.models.marketplace_models import Dealer, DealerInventory, VerifiedProduct, ProductScan
from app.db import DATABASE_URL
from app.services.ocr_service import extract_text_from_base64, parse_label_text


def _serialize_dealer(dealer: Dealer) -> dict:
    return {
        "id": str(dealer.id),
        "name": dealer.name,
        "phone_number": dealer.phone_number,
        "email": dealer.email,
        "location_lat": dealer.location_lat,
        "location_lon": dealer.location_lon,
        "is_verified": dealer.is_verified,
        "verification_status": dealer.verification_status,
        "verified_at": dealer.verified_at.isoformat() if dealer.verified_at else None,
        "regions_served": dealer.regions_served,
        "registration_date": dealer.registration_date.isoformat() if dealer.registration_date else None,
    }


async def create_dealer(
    session: AsyncSession,
    name: str,
    phone_number: str,
    email: Optional[str],
    location_lat: float,
    location_lon: float,
    regions_served: Optional[list] = None,
) -> Dealer:
    dealer = Dealer(
        name=name,
        phone_number=phone_number,
        email=email,
        location_lat=location_lat,
        location_lon=location_lon,
        location_geom=f"POINT({location_lon} {location_lat})",
        regions_served=regions_served or [],
    )
    session.add(dealer)
    await session.commit()
    await session.refresh(dealer)
    return dealer


async def list_dealers(
    session: AsyncSession,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    limit: int = 20,
) -> List[dict]:
    if lat is not None and lon is not None and "postgresql" in DATABASE_URL:
        from sqlalchemy import text

        sql = text(
            "SELECT *, ST_Distance(location_geom, ST_SetSRID(ST_Point(:lon, :lat), 4326)) AS distance_meters "
            "FROM dealers "
            "ORDER BY distance_meters ASC "
            "LIMIT :limit"
        )
        result = await session.execute(sql, {"lat": lat, "lon": lon, "limit": limit})
        return [
            {
                "id": str(row["id"]),
                "name": row["name"],
                "phone_number": row["phone_number"],
                "email": row["email"],
                "location_lat": row["location_lat"],
                "location_lon": row["location_lon"],
                "is_verified": row["is_verified"],
                "verification_status": row["verification_status"],
                "distance_meters": float(row["distance_meters"]),
            }
            for row in result.fetchall()
        ]

    from sqlalchemy import select

    result = await session.execute(select(Dealer).limit(limit))
    return [_serialize_dealer(dealer) for dealer in result.scalars().all()]


async def get_dealer(session: AsyncSession, dealer_id: str) -> Optional[dict]:
    from sqlalchemy import select

    result = await session.execute(select(Dealer).where(Dealer.id == dealer_id))
    dealer = result.scalars().first()
    return _serialize_dealer(dealer) if dealer else None


async def add_inventory_item(
    session: AsyncSession,
    dealer_id: str,
    product_name: str,
    input_type: str,
    crop_type: Optional[str],
    batch_number: Optional[str],
    manufacturer: Optional[str],
    quantity_in_stock: int,
    price_bdt: float,
    expiry_date,
) -> DealerInventory:
    item = DealerInventory(
        dealer_id=dealer_id,
        product_name=product_name,
        input_type=input_type,
        crop_type=crop_type,
        batch_number=batch_number,
        manufacturer=manufacturer,
        quantity_in_stock=quantity_in_stock,
        price_bdt=price_bdt,
        expiry_date=expiry_date,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


async def scan_product(
    session: AsyncSession,
    farmer_id_hashed: str,
    barcode: Optional[str] = None,
    qr_text: Optional[str] = None,
    image_base64: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
) -> dict:
    if not barcode and not qr_text and image_base64:
        from app.services.barcode_service import decode_barcode_base64

        decoded = decode_barcode_base64(image_base64)
        if decoded:
            if decoded.isdigit() or len(decoded) <= 20:
                barcode = decoded
            else:
                qr_text = decoded

    from sqlalchemy import select

    product = None
    if barcode:
        result = await session.execute(select(VerifiedProduct).where(VerifiedProduct.barcode == barcode))
        product = result.scalars().first()
    elif qr_text:
        result = await session.execute(select(VerifiedProduct).where(VerifiedProduct.qr_code == qr_text))
        product = result.scalars().first()

    verification_result = "UNREGISTERED"
    confidence_score = 0.0
    verified_product_id = None

    if product:
        if product.expiry_date and product.expiry_date < datetime.utcnow().date():
            verification_result = "EXPIRED"
            confidence_score = 0.6
        else:
            verification_result = "VERIFIED"
            confidence_score = 0.96
            verified_product_id = product.id
    elif image_base64:
        text = extract_text_from_base64(image_base64)
        parsed = parse_label_text(text)
        if parsed.get("product_name"):
            verification_result = "MATCH_FOUND"
            confidence_score = 0.55
        else:
            verification_result = "UNREGISTERED"
            confidence_score = 0.35

    scan = ProductScan(
        farmer_id_hashed=farmer_id_hashed,
        barcode=barcode,
        qr_text=qr_text,
        verified_product_id=verified_product_id,
        verification_result=verification_result,
        confidence_score=confidence_score,
        location_lat=lat,
        location_lon=lon,
    )
    session.add(scan)
    await session.commit()
    await session.refresh(scan)

    return {
        "scan_id": str(scan.id),
        "verification_result": verification_result,
        "confidence_score": confidence_score,
        "verified_product_id": str(verified_product_id) if verified_product_id else None,
        "barcode": barcode,
        "qr_text": qr_text,
    }


async def list_verified_products(session: AsyncSession, limit: int = 25) -> List[dict]:
    from sqlalchemy import select

    result = await session.execute(select(VerifiedProduct).limit(limit))
    products = result.scalars().all()
    return [
        {
            "id": str(product.id),
            "barcode": product.barcode,
            "product_name": product.product_name,
            "manufacturer": product.manufacturer,
            "batch_number": product.batch_number,
            "expiry_date": product.expiry_date.isoformat() if product.expiry_date else None,
            "is_verified": product.is_verified,
            "verification_source": product.verification_source,
        }
        for product in products
    ]
