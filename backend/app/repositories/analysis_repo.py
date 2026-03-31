import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Analysis


async def create(
    db: AsyncSession,
    user_id: uuid.UUID,
    filename: str,
    result: dict[str, Any],
) -> Analysis:
    analysis = Analysis(user_id=user_id, filename=filename, result=result)
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)
    return analysis


async def get_list(
    db: AsyncSession,
    user_id: uuid.UUID,
    type_filter: str | None = None,
    period_filter: datetime | None = None,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Analysis], int]:
    base = select(Analysis).where(Analysis.user_id == user_id)

    if type_filter:
        base = base.where(
            cast(Analysis.result, JSONB)["defects"].contains([{"type": type_filter}])
        )

    if period_filter:
        base = base.where(Analysis.created_at >= period_filter)

    if q:
        base = base.where(Analysis.filename.ilike(f"%{q}%"))

    total: int = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()

    rows = await db.execute(
        base.order_by(Analysis.created_at.desc()).limit(limit).offset(offset)
    )
    return list(rows.scalars().all()), total


async def get_by_id(
    db: AsyncSession,
    analysis_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Analysis | None:
    result = await db.execute(
        select(Analysis).where(
            Analysis.id == analysis_id,
            Analysis.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def get_stats(db: AsyncSession, user_id: uuid.UUID) -> dict:
    rows = await db.execute(
        select(Analysis.result).where(Analysis.user_id == user_id)
    )
    results = list(rows.scalars().all())

    total_checks = len(results)
    all_defects = [d for r in results if r for d in r.get("defects", [])]
    total_defects = len(all_defects)
    avg_confidence = (
        round(sum(d.get("confidence", 0) for d in all_defects) / total_defects, 3)
        if total_defects
        else 0.0
    )
    no_defect_photos = sum(1 for r in results if r and r.get("count", 0) == 0)
    by_type: dict[str, int] = {}
    for d in all_defects:
        t = d.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1

    return {
        "total_checks": total_checks,
        "total_defects": total_defects,
        "avg_confidence": avg_confidence,
        "no_defect_photos": no_defect_photos,
        "by_type": by_type,
    }


async def get_by_id_only(
    db: AsyncSession,
    analysis_id: uuid.UUID,
) -> Analysis | None:
    result = await db.execute(
        select(Analysis).where(Analysis.id == analysis_id)
    )
    return result.scalar_one_or_none()


async def count_today(db: AsyncSession, user_id: uuid.UUID) -> int:
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.count())
        .select_from(Analysis)
        .where(Analysis.user_id == user_id, Analysis.created_at >= today_start)
    )
    return result.scalar_one()


async def delete(db: AsyncSession, analysis: Analysis) -> None:
    await db.delete(analysis)
    await db.commit()
