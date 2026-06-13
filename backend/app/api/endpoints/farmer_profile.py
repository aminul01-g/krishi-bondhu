from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from ..db import get_db
from ..models.db_models import User, FarmerProfile
from ..core.dependencies import get_current_user

router = APIRouter()

class FarmerProfileCreate(BaseModel):
    district: Optional[str] = None
    upazila: Optional[str] = None
    crops: Optional[List[str]] = None
    land_area_bigha: Optional[float] = None
    farming_experience_years: Optional[int] = None
    phone_number: Optional[str] = None

class FarmerProfileResponse(BaseModel):
    id: int
    user_id: int
    district: Optional[str] = None
    upazila: Optional[str] = None
    crops: Optional[List[str]] = None
    land_area_bigha: Optional[float] = None
    farming_experience_years: Optional[int] = None
    phone_number: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True

@router.post("", response_model=FarmerProfileResponse, status_code=status.HTTP_200_OK)
async def upsert_farmer_profile(
    profile_data: FarmerProfileCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create or update the farmer's profile (upsert by user_id).
    """
    try:
        result = await db.execute(
            select(FarmerProfile).where(FarmerProfile.user_id == current_user.id)
        )
        existing_profile = result.scalars().first()

        if existing_profile:
            # Update existing profile
            update_data = profile_data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(existing_profile, key, value)
            await db.commit()
            await db.refresh(existing_profile)
            return existing_profile
        else:
            # Create new profile
            new_profile = FarmerProfile(
                user_id=current_user.id,
                **profile_data.model_dump(exclude_unset=True)
            )
            db.add(new_profile)
            await db.commit()
            await db.refresh(new_profile)
            return new_profile
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save profile: {str(e)}"
        )

@router.get("", response_model=dict, status_code=status.HTTP_200_OK)
async def get_farmer_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the current user's profile. Returns empty dict if not yet set.
    """
    try:
        result = await db.execute(
            select(FarmerProfile).where(FarmerProfile.user_id == current_user.id)
        )
        profile = result.scalars().first()

        if profile:
            return {
                "id": profile.id,
                "user_id": profile.user_id,
                "district": profile.district,
                "upazila": profile.upazila,
                "crops": profile.crops,
                "land_area_bigha": profile.land_area_bigha,
                "farming_experience_years": profile.farming_experience_years,
                "phone_number": profile.phone_number,
                "created_at": profile.created_at.isoformat() if profile.created_at else None,
                "updated_at": profile.updated_at.isoformat() if profile.updated_at else None
            }
        else:
            return {}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve profile: {str(e)}"
        )