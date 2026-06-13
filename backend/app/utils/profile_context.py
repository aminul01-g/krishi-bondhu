from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..models.db_models import FarmerProfile


async def get_farmer_context(user_id: int, db: AsyncSession) -> str:
    """
    Query FarmerProfile by user_id and return a formatted string for AI context.
    Returns empty string "" if no profile exists.

    Example output:
    "Farmer profile: District=Tangail, Upazila=Sakhipur, Crops=[ধান, পাট], Land=3 bigha, Experience=10 years"
    """
    try:
        result = await db.execute(
            select(FarmerProfile).where(FarmerProfile.user_id == user_id)
        )
        profile = result.scalars().first()

        if not profile:
            return ""

        # Build context string with available fields
        parts = []

        if profile.district:
            parts.append(f"District={profile.district}")

        if profile.upazila:
            parts.append(f"Upazila={profile.upazila}")

        if profile.crops:
            crops_str = ", ".join(profile.crops) if profile.crops else ""
            parts.append(f"Crops=[{crops_str}]")

        if profile.land_area_bigha is not None:
            parts.append(f"Land={profile.land_area_bigha} bigha")

        if profile.farming_experience_years is not None:
            parts.append(f"Experience={profile.farming_experience_years} years")

        if profile.phone_number:
            parts.append(f"Phone={profile.phone_number}")

        if parts:
            return "Farmer profile: " + ", ".join(parts)
        else:
            return ""

    except Exception as e:
        # Log error but don't fail the entire operation
        # The context is nice-to-have, not critical
        return ""