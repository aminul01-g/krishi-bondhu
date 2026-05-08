"""Geospatial helpers for dealer search and expert matching."""

from sqlalchemy.ext.asyncio import AsyncSession

async def find_nearest_experts(db: AsyncSession, lat: float, lon: float, limit: int = 1):
    from sqlalchemy import text

    query = text(
        """
        SELECT id, name, phone_number, email, region, ST_Distance(region_geom, ST_SetSRID(ST_Point(:lon, :lat), 4326)) AS distance_meters
        FROM agricultural_experts
        ORDER BY region_geom <-> ST_SetSRID(ST_Point(:lon, :lat), 4326)
        LIMIT :limit
        """
    )
    result = await db.execute(query, {"lon": lon, "lat": lat, "limit": limit})
    return [dict(row) for row in result.fetchall()]
