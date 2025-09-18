#!/usr/bin/env python3
"""
Build Vector Index from PostgreSQL (Profiles → Chroma/FAISS)

- Reads summarized profile rows from PostgreSQL
- Creates text chunks with metadata
- Generates embeddings and persists to Chroma, mirrors in FAISS for fast search

Run examples:
  python scripts/build_vector_index.py --batch-size 500 --max-records 5000
  python scripts/build_vector_index.py --batch-size 500   # all records
"""

import argparse
import asyncio
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.core.config import get_settings
from app.services.rag_service import DocumentChunk, VectorStore


logger = structlog.get_logger(__name__)


def _build_content(row: Dict[str, Any]) -> str:
    """Create a concise, semantically rich text for embedding."""
    wmo_id = row.get("wmo_id")
    cycle = row.get("cycle_number")
    date_str = str(row.get("profile_date"))
    lat = row.get("latitude")
    lon = row.get("longitude")
    t_min = row.get("min_temperature")
    t_max = row.get("max_temperature")
    s_min = row.get("min_salinity")
    s_max = row.get("max_salinity")
    p_max = row.get("max_pressure")

    parts: List[str] = []
    parts.append(f"ARGO profile {cycle} of float {wmo_id} on {date_str} at ({lat:.3f}, {lon:.3f}).")
    if t_min is not None and t_max is not None:
        parts.append(f"Temperature range {t_min:.2f}–{t_max:.2f} °C.")
    if s_min is not None and s_max is not None:
        parts.append(f"Salinity range {s_min:.2f}–{s_max:.2f} PSU.")
    if p_max is not None:
        parts.append(f"Max pressure {p_max:.1f} dbar.")

    return " ".join(parts)


def _build_metadata(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "type": "profile_summary",
        "data_type": "oceanographic",
        "source": "postgresql",
        "float_wmo_id": row.get("wmo_id"),
        "profile_id": row.get("id"),
        "cycle_number": row.get("cycle_number"),
        "date": str(row.get("profile_date")),
        "latitude": float(row.get("latitude")) if row.get("latitude") is not None else None,
        "longitude": float(row.get("longitude")) if row.get("longitude") is not None else None,
    }


class VectorIndexBuilder:
    def __init__(self, engine: Engine, batch_size: int = 500, max_records: Optional[int] = None):
        self.engine = engine
        self.batch_size = batch_size
        self.max_records = max_records
        self.vector_store = VectorStore()

    async def run(self) -> None:
        await self.vector_store.initialize()
        total = await self._count_profiles()
        if self.max_records is not None:
            total = min(total, self.max_records)
        logger.info("Starting vector indexing", total_records=total, batch_size=self.batch_size)

        processed = 0
        offset = 0
        while processed < total:
            remaining = total - processed
            limit = min(self.batch_size, remaining)
            rows = self._fetch_batch(limit=limit, offset=offset)
            if not rows:
                break

            documents: List[DocumentChunk] = []
            for r in rows:
                doc = DocumentChunk(
                    id=f"profile:{r['id']}",
                    content=_build_content(r),
                    metadata=_build_metadata(r),
                    source="profile_summary",
                    chunk_index=0,
                )
                documents.append(doc)

            await self.vector_store.add_documents(documents)

            processed += len(rows)
            offset += len(rows)
            logger.info("Index progress", processed=processed, total=total)

        logger.info("Vector indexing complete", processed=processed, total=total)

    async def _count_profiles(self) -> int:
        with self.engine.connect() as conn:
            res = conn.execute(text("SELECT COUNT(*) FROM argo_profiles"))
            return int(res.scalar_one())

    def _fetch_batch(self, limit: int, offset: int) -> List[Dict[str, Any]]:
        sql = text(
            """
            WITH summary AS (
              SELECT 
                m.profile_id,
                MIN(m.temperature) AS min_temperature,
                MAX(m.temperature) AS max_temperature,
                MIN(m.salinity)    AS min_salinity,
                MAX(m.salinity)    AS max_salinity,
                MAX(m.pressure)    AS max_pressure
              FROM argo_measurements m
              GROUP BY m.profile_id
            )
            SELECT 
              p.id,
              p.float_id,
              p.cycle_number,
              p.profile_date,
              p.latitude,
              p.longitude,
              s.max_pressure,
              s.min_temperature,
              s.max_temperature,
              s.min_salinity,
              s.max_salinity,
              f.wmo_id
            FROM argo_profiles p
            JOIN argo_floats f ON f.id = p.float_id
            LEFT JOIN summary s ON s.profile_id = p.id
            ORDER BY p.profile_date
            LIMIT :limit OFFSET :offset
            """
        )
        with self.engine.connect() as conn:
            res = conn.execute(sql, {"limit": limit, "offset": offset})
            cols = res.keys()
            return [dict(zip(cols, row)) for row in res.fetchall()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build vector index from PostgreSQL")
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--max-records", type=int, default=None)
    args = parser.parse_args()

    settings = get_settings()
    engine = create_engine(settings.database_url_sync)

    builder = VectorIndexBuilder(engine=engine, batch_size=args.batch_size, max_records=args.max_records)
    asyncio.run(builder.run())


if __name__ == "__main__":
    main()


