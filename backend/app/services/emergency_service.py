"""Emergency reporting, claims, and helpline service helpers."""

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime
import uuid
import logging

from geoalchemy2.elements import WKTElement

logger = logging.getLogger(__name__)

from app.models.emergency_models import (
    InsuranceProvider,
    DamageReport,
    ReportImage,
    HelplineCallLog,
)
from app.services.geospatial_service import find_nearest_experts


def _is_sqlite(session) -> bool:
    """True if this session's underlying dialect is SQLite."""
    try:
        bind = getattr(session, "bind", None)
        return bind is not None and bind.dialect.name == "sqlite"
    except Exception:
        return False


def _derive_severity(damage_estimate_percent: float, yield_loss_estimate_percent: float) -> str:
    """Triage the worst-case severity from the caller-supplied damage/yield-loss
    percentages. Thresholds:

        >= 70%  -> critical
        >= 40%  -> high
        >  0%   -> medium
        == 0%   -> low

    We take the max of the two inputs so a single severe axis still escalates.
    """
    worst = max(damage_estimate_percent or 0.0, yield_loss_estimate_percent or 0.0)
    if worst >= 70:
        return "critical"
    if worst >= 40:
        return "high"
    if worst > 0:
        return "medium"
    return "low"


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
        # On Postgres, bind a real WKTElement so it binds correctly to the
        # PostGIS Geometry column; on the SQLite fallback the column is a plain
        # Text column, so we store the WKT as text.
        location_geom=(
            f"POINT({lon} {lat})" if _is_sqlite(session)
            else WKTElement(f"POINT({lon} {lat})", srid=4326)
        ),
        damage_cause=damage_cause,
        damage_estimate_percent=damage_estimate_percent,
        yield_loss_estimate_percent=yield_loss_estimate_percent,
        severity=_derive_severity(damage_estimate_percent, yield_loss_estimate_percent),
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
        "severity": getattr(report, "severity", None),
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

    # Best-effort: attach the nearest responders so the operator has a call list
    # immediately. Never let a geo lookup failure break logging the call itself.
    if lat is not None and lon is not None:
        try:
            responders = await find_nearest_experts(session, lat, lon, limit=3)
            log.nearest_responders = responders
        except Exception as e:  # pragma: no cover - best effort
            logger.warning("Could not attach nearest responders to helpline log: %s", e)
            log.nearest_responders = []

    return log
