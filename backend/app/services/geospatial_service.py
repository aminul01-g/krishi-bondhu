"""Geospatial helpers for dealer search and expert matching."""

from sqlalchemy.ext.asyncio import AsyncSession


def _is_postgres(db) -> bool:
    """True if the session is bound to a PostgreSQL dialect.

    The spatial helpers below emit raw PostGIS SQL (ST_Distance, ST_DWithin,
    the <-> KNN operator) that SQLite (and the HF Space fallback) cannot run.
    Detecting the dialect lets us degrade gracefully instead of crashing.
    """
    try:
        bind = getattr(db, "bind", None)
        return bind is not None and bind.dialect.name == "postgresql"
    except Exception:
        return False


async def find_nearest_experts(db: AsyncSession, lat: float, lon: float, limit: int = 1):
    """Return the nearest agricultural experts to (lat, lon).

    Uses PostGIS spatial operators (ST_Distance + the <-> KNN operator). On
    non-Postgres backends (SQLite fallback / HF Spaces) there is no ST_Distance,
    so we gracefully return an empty list rather than raising.
    """
    if not _is_postgres(db):
        return []

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


async def find_nearest_dealers(
    db: AsyncSession,
    lat: float,
    lon: float,
    limit: int = 5,
    max_distance_m: float = 50000.0,
):
    """Return dealers within `max_distance_m` of (lat, lon), nearest first.

    Guarded for PostgreSQL only (uses ST_DWithin); on SQLite / HF Space it
    returns an empty list since the spatial functions are unavailable. Safe to
    call from any path — it never raises on a non-PostGIS backend.

    TODO: on the SQLite fallback we could fall back to a haversine sort over the
    denormalized location_lat/location_lon columns; left as future work to avoid
    regressing existing behavior.
    """
    if not _is_postgres(db):
        return []

    from sqlalchemy import text

    query = text(
        """
        SELECT id, name, phone_number, email, regions_served,
               ST_Distance(location_geom, ST_SetSRID(ST_Point(:lon, :lat), 4326)) AS distance_meters
        FROM dealers
        WHERE ST_DWithin(location_geom, ST_SetSRID(ST_Point(:lon, :lat), 4326), :max_distance)
        ORDER BY location_geom <-> ST_SetSRID(ST_Point(:lon, :lat), 4326)
        LIMIT :limit
        """
    )
    result = await db.execute(
        query,
        {"lon": lon, "lat": lat, "limit": limit, "max_distance": max_distance_m},
    )
    return [dict(row) for row in result.fetchall()]
