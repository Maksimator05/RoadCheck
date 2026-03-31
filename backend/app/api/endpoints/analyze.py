import logging
import os
import tempfile


from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.limits import get_daily_limit
from app.db.database import get_db
from app.db.models import User
from app.ml.inference import predict
from app.repositories import analysis_repo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyze", tags=["analyze"])

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
_MAX_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("", status_code=status.HTTP_200_OK)
async def analyze_image(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info(
        "Analyze request: filename=%s content_type=%s user_id=%s",
        file.filename, file.content_type, current_user.id,
    )

    limit = get_daily_limit(current_user.role)
    if limit is not None:
        today_count = await analysis_repo.count_today(db, current_user.id)
        if today_count >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Daily analysis limit reached ({limit})",
            )

    if file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only JPEG and PNG images are supported",
        )

    data = await file.read()
    if len(data) > _MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds 10 MB limit",
        )

    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".jpg")
    try:
        with os.fdopen(tmp_fd, "wb") as f:
            f.write(data)

        result = predict(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    analysis = await analysis_repo.create(
        db,
        user_id=current_user.id,
        filename=file.filename or "upload",
        result=result,
    )

    logger.info(
        "Analysis complete: analysis_id=%s defects=%d",
        analysis.id, result["count"],
    )

    return {**result, "analysis_id": str(analysis.id)}
