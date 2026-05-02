"""Geospatial helpers for dealer search and expert matching."""

from app.db import AsyncSessionLocal


async def find_nearest_experts(lat: float, lon: float, limit: int = 1):
    from sqlalchemy import text

    async with AsyncSessionLocal() as session:
        query = text(
            """
            SELECT id, name, phone_number, email, region, ST_Distance(region_geom, ST_SetSRID(ST_Point(:lon, :lat), 4326)) AS distance_meters
            FROM agricultural_experts
            ORDER BY region_geom <-> ST_SetSRID(ST_Point(:lon, :lat), 4326)
            LIMIT :limit
            """
        )
        result = await session.execute(query, {"lon": lon, "lat": lat, "limit": limit})
        return [dict(row) for row in result.fetchall()]
