"""Vector and embedding utility helpers."""

from sqlalchemy import text
from typing import List
from app.db import AsyncSessionLocal


async def query_vector_similarity(table_name: str, embedding_column: str, query_embedding: List[float], threshold: float = 0.7, limit: int = 5):
    query = text(
        f"""
        SELECT *, 1 - ({embedding_column} <-> :query_embedding) AS similarity
        FROM {table_name}
        WHERE 1 - ({embedding_column} <-> :query_embedding) >= :threshold
        ORDER BY ({embedding_column} <-> :query_embedding) ASC
        LIMIT :limit
        """
    )
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, {"query_embedding": query_embedding, "threshold": threshold, "limit": limit})
        return [dict(row) for row in result.fetchall()]
