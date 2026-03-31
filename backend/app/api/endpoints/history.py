import os
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.repositories import analysis_repo
from app.schemas import AnalysisListOut, AnalysisOut
from app.utils.pdf import generate_analysis_pdf

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=AnalysisListOut)
async def list_analyses(
    type: str | None = Query(None),
    period: str | None = Query(None),
    q: str | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    period_dt: datetime | None = None
    if period == "week":
        period_dt = datetime.now(timezone.utc) - timedelta(days=7)
    elif period == "month":
        period_dt = datetime.now(timezone.utc) - timedelta(days=30)

    items, total = await analysis_repo.get_list(
        db,
        user_id=current_user.id,
        type_filter=type,
        period_filter=period_dt,
        q=q,
        limit=limit,
        offset=offset,
    )
    return AnalysisListOut(items=items, total=total)



@router.get("/{analysis_id}", response_model=AnalysisOut)
async def get_analysis(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    analysis = await analysis_repo.get_by_id_only(db, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    if analysis.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return analysis


@router.get("/{analysis_id}/pdf", response_class=FileResponse)
async def get_analysis_pdf(
    analysis_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    analysis = await analysis_repo.get_by_id_only(db, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    if analysis.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    path = generate_analysis_pdf(analysis)
    background_tasks.add_task(os.remove, path)
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"report_{analysis_id}.pdf",
    )


@router.delete("/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_analysis(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    analysis = await analysis_repo.get_by_id_only(db, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    if analysis.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    await analysis_repo.delete(db, analysis)
