"""Marketplace and product verification service helpers."""

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime
import uuid

from app.models.marketplace_models import (
    Dealer,
    DealerInventory,
    VerifiedProduct,
    ProductScan,
    MarketplaceListing,
    ListingContactLog,
)
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

    scan_id_val = str(scan.id) if getattr(scan, "id", None) else uuid.uuid4().hex

    return {
        "scan_id": scan_id_val,
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


# ---------------------------------------------------------------------------
# Farmer-to-buyer crop sale listings
# ---------------------------------------------------------------------------

def mask_phone(phone: Optional[str]) -> Optional[str]:
    """Mask a phone number for public display, e.g. '01712345678' -> '017XXXXX78'.

    Keeps the first 3 and last 2 digits, masking everything in between. Handles
    Bangladeshi formats ('017...', '+88017...'); safe on short/None values.
    """
    if not phone:
        return None
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    if len(digits) < 5:
        return digits or None
    head, tail = digits[:3], digits[-2:]
    masked_len = len(digits) - 5
    return f"{head}{'X' * masked_len}{tail}"


def _serialize_listing(listing: MarketplaceListing, mask: bool = True) -> dict:
    phone = listing.seller_phone
    if mask:
        phone = mask_phone(phone)
    return {
        "id": str(listing.id),
        "title": listing.title,
        "crop": listing.crop,
        "quantity_kg": listing.quantity_kg,
        "price_per_kg": listing.price_per_kg,
        "district": listing.district,
        "upazila": listing.upazila,
        "seller_name": listing.seller_name,
        "phone_number": phone,
        "posted_date": listing.posted_date.isoformat() if listing.posted_date else None,
        "photo_url": listing.photo_url,
        "is_active": listing.is_active,
        "listing_type": listing.listing_type,
        "description": listing.description,
    }


async def list_listings(
    session: AsyncSession,
    crop: Optional[str] = None,
    district: Optional[str] = None,
    type: Optional[str] = None,
    limit: int = 50,
) -> List[dict]:
    """List active listings, optionally filtered by crop/district/type (newest first)."""
    from sqlalchemy import select

    stmt = select(MarketplaceListing).where(MarketplaceListing.is_active.is_(True))
    if crop:
        stmt = stmt.where(MarketplaceListing.crop == crop)
    if district:
        stmt = stmt.where(MarketplaceListing.district == district)
    if type:
        stmt = stmt.where(MarketplaceListing.listing_type == type)
    stmt = stmt.order_by(MarketplaceListing.posted_date.desc()).limit(limit)

    result = await session.execute(stmt)
    return [_serialize_listing(row, mask=True) for row in result.scalars().all()]


async def get_listing(session: AsyncSession, listing_id: str) -> Optional[MarketplaceListing]:
    """Fetch a single listing by id (ORM object, no serialization)."""
    from sqlalchemy import select

    result = await session.execute(
        select(MarketplaceListing).where(MarketplaceListing.id == listing_id)
    )
    return result.scalars().first()


async def create_listing(
    session: AsyncSession,
    seller_id: int,
    seller_name: str,
    seller_phone: Optional[str],
    crop: str,
    quantity_kg: int,
    price_per_kg: float,
    district: Optional[str],
    upazila: Optional[str],
    description: Optional[str] = None,
    photo_url: Optional[str] = None,
    listing_type: str = "sell",
) -> MarketplaceListing:
    """Create a new sale listing. Title is derived from crop + quantity."""
    title = f"{crop} বিক্রি হবে ({quantity_kg} কেজি)"
    listing = MarketplaceListing(
        seller_id=seller_id,
        seller_name=seller_name,
        seller_phone=seller_phone,
        crop=crop,
        title=title,
        description=description,
        quantity_kg=quantity_kg,
        price_per_kg=price_per_kg,
        district=district,
        upazila=upazila,
        photo_url=photo_url,
        listing_type=listing_type,
        is_active=True,
    )
    session.add(listing)
    await session.commit()
    await session.refresh(listing)
    return listing


async def log_listing_contact(
    session: AsyncSession,
    listing_id: str,
    buyer_id: Optional[int],
) -> Optional[MarketplaceListing]:
    """Record a contact-intent (for analytics) and return the listing so the
    caller can reveal the seller's unmasked phone number."""
    listing = await get_listing(session, listing_id)
    if not listing:
        return None
    session.add(ListingContactLog(listing_id=listing.id, buyer_id=buyer_id))
    await session.commit()
    return listing


async def list_my_listings(session: AsyncSession, seller_id: int) -> List[dict]:
    """List all of the current user's listings (incl. inactive), newest first."""
    from sqlalchemy import select

    result = await session.execute(
        select(MarketplaceListing)
        .where(MarketplaceListing.seller_id == seller_id)
        .order_by(MarketplaceListing.posted_date.desc())
    )
    return [_serialize_listing(row, mask=False) for row in result.scalars().all()]


async def delete_listing(session: AsyncSession, listing_id: str, seller_id: int) -> bool:
    """Delete a listing after verifying ownership. Returns True if deleted."""
    listing = await get_listing(session, listing_id)
    if not listing or listing.seller_id != seller_id:
        return False
    await session.delete(listing)
    await session.commit()
    return True
