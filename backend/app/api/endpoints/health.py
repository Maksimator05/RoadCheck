from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.ml.model import get_model_status

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    ml = get_model_status()
    status_code = status.HTTP_200_OK if ml["ready"] else status.HTTP_503_SERVICE_UNAVAILABLE
    payload = {
        "status": "ok" if ml["ready"] else "degraded",
        "ml": ml,
    }
    return JSONResponse(status_code=status_code, content=payload)
