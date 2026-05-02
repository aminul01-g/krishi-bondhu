"""Emergency reporting, claims, and helpline service helpers."""

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime
import uuid

from app.models.emergency_models import (
    InsuranceProvider,
    DamageReport,
    ReportImage,
    HelplineCallLog,
)


async def list_insurance_providers(session: AsyncSession) -> List[dict]:
    from sqlalchemy import select

    result = await session.execute(select(InsuranceProvider).where(InsuranceProvider.active == True))
    providers = result.scalars().all()
    return [
        {
            "id": str(provider.id),
            "name": provider.name,
            "email": provider.email,
            "phone_number": provider.phone_number,
            "api_endpoint": provider.api_endpoint,
            "active": provider.active,
        }
        for provider in providers
    ]


async def create_damage_report(
    session: AsyncSession,
    farmer_id: str,
    crop_type: str,
    growth_stage: Optional[str],
    lat: float,
    lon: float,
    damage_cause: str,
    damage_estimate_percent: float,
    yield_loss_estimate_percent: float,
    insurance_provider_id: Optional[str] = None,
    voice_statement_transcribed: Optional[str] = None,
    image_data: Optional[List[str]] = None,
) -> DamageReport:
    report = DamageReport(
        farmer_id=farmer_id,
        crop_type=crop_type,
        growth_stage=growth_stage,
        location_lat=lat,
        location_lon=lon,
        location_geom=f"POINT({lon} {lat})",
        damage_cause=damage_cause,
        damage_estimate_percent=damage_estimate_percent,
        yield_loss_estimate_percent=yield_loss_estimate_percent,
        insurance_provider_id=insurance_provider_id,
        voice_statement_transcribed=voice_statement_transcribed,
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)

    if image_data:
        for index, payload in enumerate(image_data, start=1):
            image = ReportImage(
                report_id=report.id,
                image_data=payload,
                image_order=index,
            )
            session.add(image)
        report.number_of_photos = len(image_data)
        await session.commit()
        await session.refresh(report)

    return report


async def get_damage_report(session: AsyncSession, report_id: str) -> Optional[dict]:
    from sqlalchemy import select

    result = await session.execute(select(DamageReport).where(DamageReport.id == report_id))
    report = result.scalars().first()
    if not report:
        return None
    images = [
        {
            "id": str(image.id),
            "image_url": image.image_url,
            "image_order": image.image_order,
        }
        for image in report.images
    ]
    return {
        "id": str(report.id),
        "farmer_id": report.farmer_id,
        "crop_type": report.crop_type,
        "growth_stage": report.growth_stage,
        "lat": report.location_lat,
        "lon": report.location_lon,
        "damage_cause": report.damage_cause,
        "damage_estimate_percent": report.damage_estimate_percent,
        "yield_loss_estimate_percent": report.yield_loss_estimate_percent,
        "status": report.status,
        "insurance_claim_id": report.insurance_claim_id,
        "pdf_url": report.pdf_url,
        "images": images,
        "submitted_at": report.submitted_at.isoformat() if report.submitted_at else None,
    }


async def submit_claim(
    session: AsyncSession,
    report_id: str,
    insurance_provider_id: Optional[str] = None,
) -> dict:
    from sqlalchemy import select

    result = await session.execute(select(DamageReport).where(DamageReport.id == report_id))
    report = result.scalars().first()
    if not report:
        raise ValueError("Damage report not found")

    report.status = "claimed"
    report.insurance_provider_id = insurance_provider_id or report.insurance_provider_id
    report.insurance_claim_id = str(uuid.uuid4())
    report.claimed_at = datetime.utcnow()
    await session.commit()
    await session.refresh(report)

    if report.pdf_url is None:
        try:
            from app.utils.pdf_generator import generate_damage_pdf

            report.pdf_url = generate_damage_pdf(
                {
                    "id": str(report.id),
                    "farmer_id": report.farmer_id,
                    "crop_type": report.crop_type,
                    "damage_cause": report.damage_cause,
                    "location_lat": report.location_lat,
                    "location_lon": report.location_lon,
                    "damage_estimate_percent": report.damage_estimate_percent,
                    "yield_loss_estimate_percent": report.yield_loss_estimate_percent,
                    "status": report.status,
                    "submitted_at": report.submitted_at.isoformat() if report.submitted_at else None,
                    "voice_statement_transcribed": report.voice_statement_transcribed or "",
                },
                [],
                f"backend/app/static/reports/damage_report_{report.id}.pdf"
            )
            await session.commit()
        except Exception:
            # Use best-effort PDF generation; do not block claim submission
            pass

    return {
        "report_id": str(report.id),
        "insurance_claim_id": report.insurance_claim_id,
        "status": report.status,
        "claimed_at": report.claimed_at.isoformat() if report.claimed_at else None,
        "pdf_url": report.pdf_url,
    }


async def log_helpline_call(
    session: AsyncSession,
    farmer_id: str,
    crop_type: Optional[str],
    damage_estimate: Optional[float],
    lat: Optional[float],
    lon: Optional[float],
    call_duration_seconds: Optional[int],
    operator_notes: Optional[str],
    status: str = "initiated",
) -> HelplineCallLog:
    log = HelplineCallLog(
        farmer_id=farmer_id,
        crop_type=crop_type,
        damage_estimate=damage_estimate,
        location_lat=lat,
        location_lon=lon,
        call_duration_seconds=call_duration_seconds,
        operator_notes=operator_notes,
        status=status,
    )
    session.add(log)
    await session.commit()
    await session.refresh(log)
    return log
